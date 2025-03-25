from aiogram.fsm.state import StatesGroup, State


class AuthStates(StatesGroup):
    wait_for_username = State()  # для регистрации
    wait_for_pass = State()  # для регистрации
    wait_for_pass_confirm = State()  # повторение пароля
    wait_for_login_username = State()  # для авторизации
    wait_for_login_password = State()  # для авторизации


class GiveTgStates(StatesGroup):
    wait_phone = State()
    wait_code = State()
    wait_2fa = State()
    wait_alias = State()
    wait_alias_2fa = State()


class TakeTgStates(StatesGroup):
    wait_alias = State()


class LogGroupIdState(StatesGroup):
    wait_group_id = State()


class TimeoutStates(StatesGroup):
    wait_timeout = State()


class AdminStates(StatesGroup):
    wait_ids = State()
