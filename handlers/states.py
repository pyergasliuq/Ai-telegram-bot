from aiogram.fsm.state import State, StatesGroup


class ChatStates(StatesGroup):
    in_chat = State()


class CourseworkStates(StatesGroup):
    waiting_topic = State()


class FileAnswerStates(StatesGroup):
    waiting_question = State()


class PromoStates(StatesGroup):
    waiting_code = State()


class ReferralPromoStates(StatesGroup):
    waiting_create = State()


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_user_lookup = State()
    waiting_channel_add = State()
    waiting_promo_create = State()
