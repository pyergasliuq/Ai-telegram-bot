from aiogram import Router

from handlers import account, admin, billing, callbacks, main_menu, referrals, work_menu


def build_root_router() -> Router:
    root = Router(name="root")
    root.include_routers(
        main_menu.router,
        admin.router,
        billing.router,
        account.router,
        referrals.router,
        work_menu.router,
        callbacks.router,
    )
    return root


__all__ = ["build_root_router"]
