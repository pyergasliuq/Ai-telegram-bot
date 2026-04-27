from __future__ import annotations

import logging
from dataclasses import dataclass

from core.router import AllProvidersFailed, RouteContext, chat
from services.ai_providers.base import ChatMessage
from settings import Plan, SpeedMode, TaskType

log = logging.getLogger(__name__)


@dataclass
class CourseworkResult:
    text: str
    plan_text: str
    sources_text: str
    draft_text: str
    review_text: str


PLANNER_SYSTEM = (
    "You are a strict English-only academic prompt planner. "
    "You receive a coursework topic and produce a structured plan. "
    "Output sections: GOAL, MAIN_THEMES (5-8 bullets), SUBTOPICS (10-15 bullets), "
    "SEARCH_QUERIES (8-12 short queries in Russian and English), STRICT_PROMPT (a "
    "detailed prompt for the writer model that enforces academic structure: "
    "introduction, thematic chapters with subsections, conclusion, references). "
    "Always output in English. Do not write the coursework itself."
)

SEARCH_SYSTEM = (
    "You are an English-language research assistant. You receive a coursework plan "
    "with SEARCH_QUERIES. For each query, produce: brief factual summary (3-6 "
    "sentences), 2-4 plausible source titles or known references with short "
    "context. Mix Russian-language and English-language sources where relevant. "
    "Output sections: SOURCES (numbered list), KEY_FACTS (bullet list), GAPS "
    "(short list of things still unknown). Output in English."
)

WRITER_SYSTEM_TEMPLATE = (
    "You are an academic writer. Using the supplied PLAN, SOURCES and KEY_FACTS, "
    "write a complete coursework text in {language}. Follow the STRICT_PROMPT "
    "from the plan. Use formal academic tone, headings and subheadings, "
    "introduction, thematic chapters with subsections, conclusion and a list of "
    "references at the end. Aim for {min_chars}-{max_chars} characters, do not "
    "truncate. Output the FINAL coursework text only."
)

VERIFIER_SYSTEM_TEMPLATE = (
    "You are a strict academic editor and verifier. You receive a coursework "
    "draft and the original plan. Check facts, logic, completeness, formatting "
    "and style. Fix issues silently and return the final polished coursework "
    "text in {language}. Keep all chapters, subsections and references. Output "
    "the FINAL polished text only, no commentary."
)


async def run_coursework(
    *,
    topic: str,
    language: str,
    plan: Plan = Plan.MAX,
    min_chars: int = 12000,
    max_chars: int = 20000,
) -> CourseworkResult:
    plan_ctx = RouteContext(
        plan=plan,
        task_type=TaskType.TEXT_REASONING,
        speed_mode=SpeedMode.MAX,
        language="en",
    )
    plan_messages: list[ChatMessage] = [
        ChatMessage(role="system", content=PLANNER_SYSTEM),
        ChatMessage(role="user", content=f"Coursework topic: {topic}\n\nProduce the plan."),
    ]
    plan_resp = await chat(plan_ctx, plan_messages, temperature=0.3, max_tokens=1800)
    plan_text = plan_resp.text

    search_ctx = RouteContext(
        plan=plan,
        task_type=TaskType.SEARCH,
        speed_mode=SpeedMode.BALANCE,
        language="en",
    )
    search_messages: list[ChatMessage] = [
        ChatMessage(role="system", content=SEARCH_SYSTEM),
        ChatMessage(role="user", content=f"Plan:\n{plan_text}"),
    ]
    try:
        search_resp = await chat(search_ctx, search_messages, temperature=0.3, max_tokens=2000)
        sources_text = search_resp.text
    except AllProvidersFailed:
        sources_text = "SOURCES: (search stage unavailable)\nKEY_FACTS: (use plan only)\nGAPS: (n/a)"

    writer_system = WRITER_SYSTEM_TEMPLATE.format(
        language="Russian" if language == "ru" else "English",
        min_chars=min_chars,
        max_chars=max_chars,
    )
    writer_ctx = RouteContext(
        plan=plan,
        task_type=TaskType.TEXT_REASONING,
        speed_mode=SpeedMode.MAX,
        language=language,
    )
    writer_messages: list[ChatMessage] = [
        ChatMessage(role="system", content=writer_system),
        ChatMessage(
            role="user",
            content=(
                f"PLAN:\n{plan_text}\n\nSOURCES_AND_FACTS:\n{sources_text}\n\n"
                f"Original topic: {topic}.\nWrite the full coursework now."
            ),
        ),
    ]
    writer_resp = await chat(writer_ctx, writer_messages, temperature=0.6, max_tokens=8000)
    draft_text = writer_resp.text

    verifier_system = VERIFIER_SYSTEM_TEMPLATE.format(
        language="Russian" if language == "ru" else "English",
    )
    verifier_ctx = RouteContext(
        plan=plan,
        task_type=TaskType.VERIFIER,
        speed_mode=SpeedMode.MAX,
        language=language,
    )
    verifier_messages: list[ChatMessage] = [
        ChatMessage(role="system", content=verifier_system),
        ChatMessage(
            role="user",
            content=(
                f"PLAN:\n{plan_text}\n\nDRAFT:\n{draft_text}\n\n"
                "Return the final polished coursework text only."
            ),
        ),
    ]
    try:
        verifier_resp = await chat(verifier_ctx, verifier_messages, temperature=0.3, max_tokens=8000)
        final_text = verifier_resp.text
    except AllProvidersFailed:
        final_text = draft_text

    return CourseworkResult(
        text=final_text,
        plan_text=plan_text,
        sources_text=sources_text,
        draft_text=draft_text,
        review_text=final_text,
    )
