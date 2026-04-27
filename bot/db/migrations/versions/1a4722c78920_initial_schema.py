from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '1a4722c78920'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table('broadcast_jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('admin_id', sa.BigInteger(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('filter_plan', sa.String(length=16), nullable=True),
    sa.Column('sent', sa.Integer(), nullable=False),
    sa.Column('failed', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('broadcast_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_broadcast_jobs_admin_id'), ['admin_id'], unique=False)

    op.create_table('crypto_rate_cache',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('asset', sa.String(length=16), nullable=False),
    sa.Column('usd_per_unit', sa.Float(), nullable=False),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('asset')
    )
    op.create_table('promo_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('discount_percent', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(length=256), nullable=True),
    sa.Column('creator_user_id', sa.BigInteger(), nullable=True),
    sa.Column('min_plan_required', sa.String(length=16), nullable=True),
    sa.Column('max_uses', sa.Integer(), nullable=False),
    sa.Column('used_count', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('sponsor_only', sa.Boolean(), nullable=False),
    sa.Column('requires_active_subscription', sa.Boolean(), nullable=False),
    sa.Column('is_user_referral', sa.Boolean(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('promo_codes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_promo_codes_code'), ['code'], unique=True)
        batch_op.create_index(batch_op.f('ix_promo_codes_creator_user_id'), ['creator_user_id'], unique=False)

    op.create_table('provider_statuses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('provider_name', sa.String(length=32), nullable=False),
    sa.Column('model', sa.String(length=128), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('last_fail_time', sa.DateTime(), nullable=True),
    sa.Column('fail_reason', sa.String(length=256), nullable=True),
    sa.Column('cooldown_until', sa.DateTime(), nullable=True),
    sa.Column('success_count', sa.Integer(), nullable=False),
    sa.Column('fail_count', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('provider_name', 'model', name='uq_provider_model')
    )
    with op.batch_alter_table('provider_statuses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_provider_statuses_provider_name'), ['provider_name'], unique=False)

    op.create_table('referrals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('inviter_user_id', sa.BigInteger(), nullable=False),
    sa.Column('invited_user_id', sa.BigInteger(), nullable=False),
    sa.Column('invited_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('reward_granted', sa.Boolean(), nullable=False),
    sa.Column('reward_type', sa.String(length=32), nullable=True),
    sa.Column('paid_user', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('invited_user_id', name='uq_invited')
    )
    with op.batch_alter_table('referrals', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_referrals_invited_user_id'), ['invited_user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_referrals_inviter_user_id'), ['inviter_user_id'], unique=False)

    op.create_table('required_channels',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('channel_username', sa.String(length=64), nullable=False),
    sa.Column('channel_id', sa.BigInteger(), nullable=True),
    sa.Column('title', sa.String(length=128), nullable=True),
    sa.Column('invite_link', sa.String(length=256), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('channel_username')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('telegram_id', sa.BigInteger(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.Column('full_name', sa.String(length=128), nullable=True),
    sa.Column('current_plan', sa.String(length=16), nullable=False),
    sa.Column('language', sa.String(length=4), nullable=False),
    sa.Column('subscription_expires_at', sa.DateTime(), nullable=True),
    sa.Column('trial_used_plans', sa.JSON(), nullable=False),
    sa.Column('ref_code', sa.String(length=16), nullable=False),
    sa.Column('referred_by', sa.BigInteger(), nullable=True),
    sa.Column('bonus_text_requests', sa.Integer(), nullable=False),
    sa.Column('is_banned', sa.Boolean(), nullable=False),
    sa.Column('is_muted', sa.Boolean(), nullable=False),
    sa.Column('channels_verified', sa.Boolean(), nullable=False),
    sa.Column('settings_data', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_ref_code'), ['ref_code'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_referred_by'), ['referred_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_telegram_id'), ['telegram_id'], unique=True)

    op.create_table('chat_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=128), nullable=False),
    sa.Column('summary', sa.JSON(), nullable=False),
    sa.Column('meta', sa.JSON(), nullable=False),
    sa.Column('archived', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('chat_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_chat_sessions_user_id'), ['user_id'], unique=False)

    op.create_table('daily_quotas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('text_used', sa.Integer(), nullable=False),
    sa.Column('text_limit', sa.Integer(), nullable=False),
    sa.Column('img_used', sa.Integer(), nullable=False),
    sa.Column('img_limit', sa.Integer(), nullable=False),
    sa.Column('voice_used', sa.Integer(), nullable=False),
    sa.Column('voice_limit', sa.Integer(), nullable=False),
    sa.Column('stt_used', sa.Integer(), nullable=False),
    sa.Column('stt_limit', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'date', name='uq_user_date')
    )
    with op.batch_alter_table('daily_quotas', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_daily_quotas_date'), ['date'], unique=False)
        batch_op.create_index(batch_op.f('ix_daily_quotas_user_id'), ['user_id'], unique=False)

    op.create_table('payments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('plan', sa.String(length=16), nullable=False),
    sa.Column('duration_key', sa.String(length=8), nullable=False),
    sa.Column('method', sa.String(length=16), nullable=False),
    sa.Column('asset', sa.String(length=16), nullable=True),
    sa.Column('amount_usd', sa.Float(), nullable=False),
    sa.Column('amount_native', sa.String(length=64), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('invoice_id', sa.String(length=128), nullable=True),
    sa.Column('extra', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_payments_invoice_id'), ['invoice_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_payments_user_id'), ['user_id'], unique=False)

    op.create_table('promo_usages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('promo_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('used_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['promo_id'], ['promo_codes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('promo_id', 'user_id', name='uq_promo_user')
    )
    with op.batch_alter_table('promo_usages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_promo_usages_promo_id'), ['promo_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_promo_usages_user_id'), ['user_id'], unique=False)

    op.create_table('subscriptions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('plan', sa.String(length=16), nullable=False),
    sa.Column('starts_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('payment_method', sa.String(length=16), nullable=False),
    sa.Column('duration_days', sa.Integer(), nullable=False),
    sa.Column('trial', sa.Boolean(), nullable=False),
    sa.Column('promo_code', sa.String(length=32), nullable=True),
    sa.Column('amount_usd', sa.Float(), nullable=False),
    sa.Column('extra', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.create_index('ix_subs_user_active', ['user_id', 'expires_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_subscriptions_user_id'), ['user_id'], unique=False)

    op.create_table('messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('chat_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('tokens_in', sa.Integer(), nullable=False),
    sa.Column('tokens_out', sa.Integer(), nullable=False),
    sa.Column('provider', sa.String(length=32), nullable=True),
    sa.Column('model', sa.String(length=128), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['chat_id'], ['chat_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.create_index('ix_messages_chat_created', ['chat_id', 'created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_messages_chat_id'), ['chat_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_messages_created_at'), ['created_at'], unique=False)

def downgrade() -> None:
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_messages_created_at'))
        batch_op.drop_index(batch_op.f('ix_messages_chat_id'))
        batch_op.drop_index('ix_messages_chat_created')

    op.drop_table('messages')
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_subscriptions_user_id'))
        batch_op.drop_index('ix_subs_user_active')

    op.drop_table('subscriptions')
    with op.batch_alter_table('promo_usages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_promo_usages_user_id'))
        batch_op.drop_index(batch_op.f('ix_promo_usages_promo_id'))

    op.drop_table('promo_usages')
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_payments_user_id'))
        batch_op.drop_index(batch_op.f('ix_payments_invoice_id'))

    op.drop_table('payments')
    with op.batch_alter_table('daily_quotas', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_daily_quotas_user_id'))
        batch_op.drop_index(batch_op.f('ix_daily_quotas_date'))

    op.drop_table('daily_quotas')
    with op.batch_alter_table('chat_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_chat_sessions_user_id'))

    op.drop_table('chat_sessions')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_telegram_id'))
        batch_op.drop_index(batch_op.f('ix_users_referred_by'))
        batch_op.drop_index(batch_op.f('ix_users_ref_code'))

    op.drop_table('users')
    op.drop_table('required_channels')
    with op.batch_alter_table('referrals', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_referrals_inviter_user_id'))
        batch_op.drop_index(batch_op.f('ix_referrals_invited_user_id'))

    op.drop_table('referrals')
    with op.batch_alter_table('provider_statuses', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_provider_statuses_provider_name'))

    op.drop_table('provider_statuses')
    with op.batch_alter_table('promo_codes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_promo_codes_creator_user_id'))
        batch_op.drop_index(batch_op.f('ix_promo_codes_code'))

    op.drop_table('promo_codes')
    op.drop_table('crypto_rate_cache')
    with op.batch_alter_table('broadcast_jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_broadcast_jobs_admin_id'))

    op.drop_table('broadcast_jobs')
