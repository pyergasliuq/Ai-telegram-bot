from __future__ import annotations

import logging
from dataclasses import dataclass

from core.router import AllProvidersFailed, RouteContext, chat
from services.ai_providers.base import ChatMessage
from settings import (
    MOOD_PROMPTS,
    PLAN_FEATURES,
    TASK_PROMPTS,
    Mood,
    Plan,
    SpeedMode,
    StageMode,
    TaskPreset,
    TaskType,
)

log = logging.getLogger(__name__)


@dataclass
class PipelineRequest:
    user_message: str
    plan: Plan
    language: str
    speed_mode: SpeedMode
    stage_mode: StageMode
    mood: Mood
    task_preset: TaskPreset
    task_type: TaskType
    history: list[ChatMessage]
    summary_text: str = ""


@dataclass
class PipelineResult:
    text: str
    provider: str
    model: str
    stages_used: int


def _final_lang_instruction(lang: str) -> str:
    if lang == "en":
        return "You MUST output the FINAL answer in English."
    return "You MUST output the FINAL answer in Russian."


def _system_prompt(req: PipelineRequest) -> str:
    parts: list[str] = []
    parts.append(MOOD_PROMPTS[req.mood])
    parts.append(TASK_PROMPTS[req.task_preset])
    parts.append(_final_lang_instruction(req.language))
    if req.summary_text:
        parts.append(f"Conversation summary so far: {req.summary_text}")
    return "\n\n".join(parts)


def _enforce_stages(plan: Plan, stage: StageMode) -> StageMode:
    allowed = PLAN_FEATURES[plan]["stages"]
    if stage in allowed:
        return stage
    return allowed[-1]


async def run(req: PipelineRequest) -> PipelineResult:
    stage = _enforce_stages(req.plan, req.stage_mode)

    system = _system_prompt(req)
    base_messages: list[ChatMessage] = [ChatMessage(role="system", content=system)]
    base_messages.extend(req.history)
    base_messages.append(ChatMessage(role="user", content=req.user_message))

    if stage == StageMode.ONE:
        ctx = RouteContext(plan=req.plan, task_type=req.task_type, speed_mode=req.speed_mode, language=req.language)
        resp = await chat(ctx, base_messages)
        return PipelineResult(text=resp.text, provider=resp.provider, model=resp.model, stages_used=1)

    refine_ctx = RouteContext(plan=req.plan, task_type=TaskType.SEARCH, speed_mode=SpeedMode.BALANCE, language=req.language)
    refine_messages: list[ChatMessage] = [
        ChatMessage(
            role="system",
            content=(
                "You are an English-language research and prompt-refinement model. "
                "Take the user's request, expand it, fetch any factual context you know, "
                "and produce: (1) a concise English research brief with key facts and "
                "potential sources/links if relevant, (2) a clean refined prompt for the "
                "downstream reasoning model. Output sections 'BRIEF:' and 'REFINED:'. "
                "The downstream model will produce the final user-facing answer in the user's language."
            ),
        ),
        ChatMessage(role="user", content=req.user_message),
    ]
    try:
        refine_resp = await chat(refine_ctx, refine_messages, temperature=0.3, max_tokens=900)
        brief = refine_resp.text
    except AllProvidersFailed:
        brief = req.user_message

    main_ctx = RouteContext(plan=req.plan, task_type=req.task_type, speed_mode=req.speed_mode, language=req.language)
    main_messages: list[ChatMessage] = [
        ChatMessage(role="system", content=system),
        *req.history,
        ChatMessage(
            role="user",
            content=(
                f"Research brief and refined prompt:\n{brief}\n\n"
                f"Original user message:\n{req.user_message}\n\n"
                f"{_final_lang_instruction(req.language)}"
            ),
        ),
    ]
    main_resp = await chat(main_ctx, main_messages, temperature=0.7, max_tokens=1400)

    if stage == StageMode.TWO:
        return PipelineResult(
            text=main_resp.text,
            provider=main_resp.provider,
            model=main_resp.model,
            stages_used=2,
        )

    verify_ctx = RouteContext(plan=req.plan, task_type=TaskType.VERIFIER, speed_mode=SpeedMode.MAX, language=req.language)
    verify_messages: list[ChatMessage] = [
        ChatMessage(
            role="system",
            content=(
                "You are a strict verifier, editor and translator. You receive a draft answer "
                "and the original user request. Check facts and consistency, fix logic and "
                "style, and produce a final polished answer. " + _final_lang_instruction(req.language)
            ),
        ),
        ChatMessage(
            role="user",
            content=(
                f"Original user request:\n{req.user_message}\n\n"
                f"Draft answer:\n{main_resp.text}\n\n"
                f"Produce only the final answer. {_final_lang_instruction(req.language)}"
            ),
        ),
    ]
    try:
        verify_resp = await chat(verify_ctx, verify_messages, temperature=0.4, max_tokens=1600)
        return PipelineResult(
            text=verify_resp.text,
            provider=verify_resp.provider,
            model=verify_resp.model,
            stages_used=3,
        )
    except AllProvidersFailed:
        return PipelineResult(
            text=main_resp.text,
            provider=main_resp.provider,
            model=main_resp.model,
            stages_used=2,
        )
