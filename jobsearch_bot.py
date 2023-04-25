import json
import logging
import os
import sys
import time
from http import HTTPStatus
from typing import Dict

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (NotForSendingError, NotOkAPIResponseCodeError,
                        UnexpectedAPIResponseError)

load_dotenv()

TOKENS = ('TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'API_KEY', 'API_ID')

TELEGRAM_TOKEN = os.getenv(TOKENS[0])
TELEGRAM_CHAT_ID = os.getenv(TOKENS[1])
API_KEY = os.getenv(TOKENS[2])
API_ID = os.getenv(TOKENS[3])

RETRY_PERIOD = 60 * 10
COUNTRY = 'mx' # Change this to the relevant country code
ENDPOINT = 'https://api.adzuna.com/v1/api/jobs/' + COUNTRY + '/search/1'
PARAMS = {
    'app_id': API_ID,
    'app_key': API_KEY,
    'results_per_page': 5, # You can change this number based on your requirements
    'what': 'python', # Replace this with the desired job title or keyword
    'sort_by': 'date',
    'content-type': 'application/json'
}


def check_tokens() -> None:
    """
    Проверяет наличие значений у переменных окружения, которые необходимы для
    работы программы.
    """
    fails = [token for token in TOKENS if not globals()[token]]
    if not fails:
        return
    message = f'Не найдены значения переменных окружения: {fails}'
    logging.critical(message)
    raise ValueError(message)


def send_message(bot, message: str) -> None:
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.debug(f'Начало отправки сообщения в Telegram: {message}')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=json.dumps(message, ensure_ascii=False)
        )
    except telegram.error.TelegramError as error:
        logging.exception(
            f'При отправке в Telegram сообщения {message} '
            f'возникла ошибка: {error}'
        )
    else:
        logging.debug(f'В Telegram отправлено сообщение {message}.')


def get_api_answer() -> Dict:
    """
    Делает GET-запрос к эндпоинту API-сервиса и возвращает
    ответ, приведенный к типам данных Python.
    """
    request_params = dict(
        url=ENDPOINT,
        params=PARAMS
    )
    logging.info(
        (
            'Попытка отправки GET-запроса к эндпоинту {url}, '
            'с параметрами: params= {params}.'
        ).format(**request_params)
    )
    try:
        response = requests.get(**request_params)
    except requests.RequestException as error:
        raise ConnectionError(
            (
                'Во время подключения к эндпоинту {url} произошла '
                'непредвиденная ошибка: {error}. '
                'params = {params};'
            ).format(error=error, **request_params)
        ) from error
    if response.status_code != HTTPStatus.OK:
        raise NotOkAPIResponseCodeError(
            'Ответ сервера не является успешным:'
            f' http_code = {response.status_code};'
            f' reason = {response.reason}; content = {response.text}'
        )
    logging.info('Ответ на запрос к API получен.')
    return response.json()


def parse_status(vacancy: Dict) -> str:
    """
    Извлекает из информации о конкретной вакансии нужные детали и формирует 
    сообщение для дальнейшей отправки.
    """
    if 'title' not in vacancy:
        raise KeyError(
            'В ответе API отсутствуют ключ "title": '
            f'vacancy = {vacancy}.'
        )

    title = vacancy['title']

    if 'location' not in vacancy:
        raise KeyError(
            'В ответе API отсутствуют ключ "location": '
            f'vacancy = {vacancy}.'
        )
    
    location = vacancy['location']['display_name']

    if 'company' not in vacancy:
        raise KeyError(
            'В ответе API отсутствуют ключ "company": '
            f'vacancy = {vacancy}.'
        )
    
    company = vacancy['company']['display_name']

    if 'redirect_url' not in vacancy:
        raise KeyError(
            'В ответе API отсутствуют ключ "redirect_url": '
            f'vacancy = {vacancy}.'
        )
    
    redirect_url = vacancy['redirect_url']

    return (
        f'{title} in {location}, for company: {company}. Link: {redirect_url}'
    )


def check_response(response: Dict) -> None:
    """Проверяет структуру переданного ответа на соответствие документации."""
    logging.debug('Начало проверки ответа API.')
    if not isinstance(response, dict):
        raise TypeError(
            f'Переданный ответ не является словарем. Получен {type(response)}.'
        )

    if 'results' not in response:
        raise UnexpectedAPIResponseError(
            'В переданном ответе отсутствуют необходимый ключ "results", '
            f'response = {response}.'
        )

    results = response['results']

    if not isinstance(results, list):
        raise TypeError(
            'В переданном ответе под ключом "results" пришел не список. '
            f'Получен {type(response)}.'
        )
    logging.debug('Проверка ответа API завершена.')


def main() -> None:
    """Запускает Telegram бот."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    message = 'Бот начал работу.'
    logging.info(message)
    send_message(bot, message)

    last_vacancy_id = None

    while True:
        try:
            response = get_api_answer()
            check_response(response)
            vacancies = response['results']
            new_vacancies_found = False

            for vacancy in vacancies:
                if last_vacancy_id is None or vacancy['id'] != last_vacancy_id:
                    send_message(bot, parse_status(vacancy))
                    new_vacancies_found = True
                else:
                    break
            
            if new_vacancies_found:
                last_vacancy_id = vacancies[0]['id']

        except NotForSendingError as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(asctime)s [%(levelname)s] - '
            '(%(filename)s).%(funcName)s:%(lineno)d - %(message)s'
        ),
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    main()