from aiogram.fsm.state import StatesGroup, State

class AuthStates(StatesGroup):
    wait_for_username = State() # для регистрации
    wait_for_pass = State() # для регистрации
    wait_for_pass_confirm = State() # повторение пароля
    wait_for_login_username = State() # для авторизации
    wait_for_login_password = State() # для авторизации
