import os
import sys

import pytest_timeout

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir_content = os.listdir(BASE_DIR)
HOMEWORK_FILENAME = 'jobsearch_bot.py'

if (
    HOMEWORK_FILENAME not in root_dir_content or os.path.isdir(
        os.path.join(BASE_DIR, HOMEWORK_FILENAME))
):
    assert False, (
        f'В директории `{BASE_DIR}` не найден файл '
        f'с домашней работой `{HOMEWORK_FILENAME}`. '
    )

pytest_plugins = [
    'tests.fixtures.fixture_data'
]

TIMEOUT_ASSERT_MSG = (
    'Выполнение тестов прервано ввиду зависания проверки.\n'
    'Вероятные причины зависания:\n'
    '1. Наличие исполняемого кода в глобальной зоне видимости (например, '
    'вызов `main()`). Исполняемый код следует закрыть конструкцией '
    '`if __name__ == "__main__":\n'
    '2. Внутри цикла `while True` в функции `main` инструкция '
    '`time.sleep()` должная выполняться при любом сценарии работы. '
    'Невыполнение данного условия может стать причиной зависания тестов.'
)


def write_timeout_reasons(text, stream=None):
    """Write possible reasons of tests timeout to stream.

    The function to replace pytest_timeout traceback output with possible
    reasons of tests timeout.
    Appears only when `thread` method is used.
    """
    if stream is None:
        stream = sys.stderr
    text = TIMEOUT_ASSERT_MSG
    stream.write(text)


pytest_timeout.write = write_timeout_reasons

os.environ['API_KEY'] = 'id4api'
os.environ['API_KEY'] = 's0m3-api-k3y'
os.environ['TELEGRAM_TOKEN'] = '1234:abcdefg'
os.environ['TELEGRAM_CHAT_ID'] = '12345'
