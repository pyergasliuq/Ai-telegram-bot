from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_plan: Mapped[str] = mapped_column(String(16), default="free")
    language: Mapped[str] = mapped_column(String(4), default="ru")
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trial_used_plans: Mapped[list[str]] = mapped_column(JSON, default=list)

    ref_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    referred_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    bonus_text_requests: Mapped[int] = mapped_column(Integer, default=0)
    bonus_image_requests: Mapped[int] = mapped_column(Integer, default=0)
    bonus_voice_requests: Mapped[int] = mapped_column(Integer, default=0)
    bonus_coursework_requests: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)
    channels_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    settings_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    chats: Mapped[list[ChatSession]] = relationship(back_populates="user", cascade="all, delete-orphan")
    quotas: Mapped[list[DailyQuota]] = relationship(back_populates="user", cascade="all, delete-orphan")
    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(128), default="Новый чат")
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="chats")
    messages: Mapped[list[Message]] = relationship(back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    chat: Mapped[ChatSession] = relationship(back_populates="messages")


class DailyQuota(Base):
    __tablename__ = "daily_quotas"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    text_used: Mapped[int] = mapped_column(Integer, default=0)
    text_limit: Mapped[int] = mapped_column(Integer, default=0)
    img_used: Mapped[int] = mapped_column(Integer, default=0)
    img_limit: Mapped[int] = mapped_column(Integer, default=0)
    voice_used: Mapped[int] = mapped_column(Integer, default=0)
    voice_limit: Mapped[int] = mapped_column(Integer, default=0)
    stt_used: Mapped[int] = mapped_column(Integer, default=0)
    stt_limit: Mapped[int] = mapped_column(Integer, default=0)
    coursework_used: Mapped[int] = mapped_column(Integer, default=0)
    coursework_limit: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(back_populates="quotas")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan: Mapped[str] = mapped_column(String(16))
    starts_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    payment_method: Mapped[str] = mapped_column(String(16))
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    trial: Mapped[bool] = mapped_column(Boolean, default=False)
    promo_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount_usd: Mapped[float] = mapped_column(default=0.0)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="subscriptions")


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (UniqueConstraint("invited_user_id", name="uq_invited"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inviter_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    invited_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    invited_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reward_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    reward_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    paid_user: Mapped[bool] = mapped_column(Boolean, default=False)


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    discount_percent: Mapped[int] = mapped_column(Integer, default=10)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    creator_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    min_plan_required: Mapped[str | None] = mapped_column(String(16), nullable=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=0)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sponsor_only: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_active_subscription: Mapped[bool] = mapped_column(Boolean, default=False)
    is_user_referral: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PromoUsage(Base):
    __tablename__ = "promo_usages"
    __table_args__ = (UniqueConstraint("promo_id", "user_id", name="uq_promo_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    promo_id: Mapped[int] = mapped_column(ForeignKey("promo_codes.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    used_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RequiredChannel(Base):
    __tablename__ = "required_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_username: Mapped[str] = mapped_column(String(64), unique=True)
    channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    invite_link: Mapped[str | None] = mapped_column(String(256), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProviderStatus(Base):
    __tablename__ = "provider_statuses"
    __table_args__ = (UniqueConstraint("provider_name", "model", name="uq_provider_model"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_name: Mapped[str] = mapped_column(String(32), index=True)
    model: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fail_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fail_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan: Mapped[str] = mapped_column(String(16))
    duration_key: Mapped[str] = mapped_column(String(8))
    method: Mapped[str] = mapped_column(String(16))
    asset: Mapped[str | None] = mapped_column(String(16), nullable=True)
    amount_usd: Mapped[float] = mapped_column(default=0.0)
    amount_native: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    invoice_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class CryptoRateCache(Base):
    __tablename__ = "crypto_rate_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset: Mapped[str] = mapped_column(String(16), unique=True)
    usd_per_unit: Mapped[float] = mapped_column()
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BroadcastJob(Base):
    __tablename__ = "broadcast_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, index=True)
    text: Mapped[str] = mapped_column(Text)
    filter_plan: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sent: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FSMState(Base):
    __tablename__ = "fsm_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(BigInteger, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    thread_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("bot_id", "chat_id", "user_id", "thread_id", name="uq_fsm_key"),
    )


Index("ix_messages_chat_created", Message.chat_id, Message.created_at)
Index("ix_subs_user_active", Subscription.user_id, Subscription.expires_at)
