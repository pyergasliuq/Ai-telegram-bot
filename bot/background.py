from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from bot.db.models import Payment
from bot.db.session import async_session_maker
from bot.handlers.billing import confirm_crypto_invoice
from bot.services.payments import crypto_bot

log = logging.getLogger(__name__)


async def poll_crypto_invoices() -> None:
    if not crypto_bot.available:
        log.info("crypto-bot polling disabled")
        return
    while True:
        try:
            async with async_session_maker() as session:
                stmt = select(Payment).where(Payment.method == "crypto", Payment.status == "pending")
                pending = list((await session.execute(stmt)).scalars().all())
                if not pending:
                    pass
                else:
                    invoice_ids = [p.invoice_id for p in pending if p.invoice_id]
                    if invoice_ids:
                        try:
                            invoices = await crypto_bot.get_invoices(invoice_ids)
                        except Exception as e:
                            log.warning("crypto-bot poll failed: %s", e)
                            invoices = []
                        idx = {str(i.get("invoice_id")): i for i in invoices}
                        for p in pending:
                            inv = idx.get(str(p.invoice_id))
                            if inv and inv.get("status") == "paid":
                                await confirm_crypto_invoice(session, p)
                        await session.commit()
        except Exception:
            log.exception("crypto poll loop error")
        await asyncio.sleep(30)
