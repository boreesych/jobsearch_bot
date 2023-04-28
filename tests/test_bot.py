import inspect
import logging
import platform
import re
import time
from http import HTTPStatus

import pytest
import requests
import telegram

import utils

old_sleep = time.sleep


def create_mock_response_get_with_custom_status_and_data(http_status, data):
    def mocked_response(*args, **kwargs):
        return utils.MockResponseGET(
            *args, http_status=http_status, data=data, **kwargs
        )

    return mocked_response


def get_mock_telegram_bot(monkeypatch, random_message):
    def mock_telegram_bot(random_message=random_message, *args, **kwargs):
        return utils.MockTelegramBot(*args, message=random_message, **kwargs)

    monkeypatch.setattr(telegram, 'Bot', mock_telegram_bot)
    return telegram.Bot(token='')


class TestHomework:
    ENV_VARS = ('TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'API_KEY', 'API_ID')
    HOMEWORK_CONSTANTS = ('API_KEY', 'API_ID', 'TELEGRAM_TOKEN',
                          'TELEGRAM_CHAT_ID', 'RETRY_PERIOD',
                          'ENDPOINT', 'COUNTRY', 'PARAMS')
    PARAMS_KEYS = {
        'app_id', 'app_key', 'results_per_page', 'what', 'sort_by',
        'content-type'
    }
    HOMEWORK_FUNC_WITH_PARAMS_QTY = {
        'send_message': 2,
        'get_api_answer': 0,
        'check_response': 1,
        'parse_vacancy': 1,
        'check_tokens': 0,
        'main': 0
    }
    RETRY_PERIOD = 600
    INVALID_RESPONSES = {
        'no_results_key': utils.InvalidData(
            {
                'count': 13798,
                'mean': 67135.91
            },
            'results'
        ),
        'not_dict_response': utils.InvalidData(
            [{
                'count': 13798,
                'mean': 67135.91,
                'results': [
                    {
                        'company': {'display_name': 'Fake Company'},
                        'location': {'display_name': 'Edinburgh, Scotland'},
                        'title': 'Python Engineer',
                        'redirect_url': 'https://www.adzuna.co.uk/continuation'
                    }
                ]
            }],
            None
        ),
        'homeworks_not_in_list': utils.InvalidData(
            {
                'count': 13798,
                'mean': 67135.91,
                'results': {
                    'company': {'display_name': 'Fake Company'},
                    'location': {'display_name': 'Edinburgh, Scotland'},
                    'title': 'Python Engineer',
                    'redirect_url': 'https://www.adzuna.co.uk/continuation'
                }
            },
            None
        )
    }
    NOT_OK_RESPONSES = {
        500: (
            create_mock_response_get_with_custom_status_and_data(
                http_status=HTTPStatus.INTERNAL_SERVER_ERROR,
                data={}
            )
        ),
        401: (
            create_mock_response_get_with_custom_status_and_data(
                http_status=HTTPStatus.UNAUTHORIZED,
                data={
                    'exception': 'AUTH_FAIL',
                    'display': 'Authorisation failed'
                }
            )
        ),
        204: (
            create_mock_response_get_with_custom_status_and_data(
                http_status=HTTPStatus.NO_CONTENT,
                data={}
            )
        )
    }

    @pytest.mark.timeout(1, method='thread')
    def test_homework_const(self, homework_module):
        for const in self.HOMEWORK_CONSTANTS:
            utils.check_default_var_exists(homework_module, const)
        assert getattr(homework_module, 'RETRY_PERIOD') == self.RETRY_PERIOD, (
            'Не изменяйте переменную `RETRY_PERIOD`, её значение должно '
            f'быть равно `{self.RETRY_PERIOD}`.'
        )
        student_params = homework_module.PARAMS
        missing_keys = self.PARAMS_KEYS - set(student_params)
        verbose_missing_keys = 'ключ' if len(missing_keys) < 2 else 'ключи'
        assert not missing_keys, (
            'Убедитесь, что словарь `PARAMS` содержит '
            f'{verbose_missing_keys} `{"`, `".join(missing_keys)}`.'
        )

        assert_msg_template = (
            'Убедитесь, что в словаре `PARAMS` значением ключа `{key}` '
            '{description}.'
        )
        result_per_page_key = 'results_per_page'
        min_results_per_page = 5
        assert student_params[result_per_page_key] >= min_results_per_page, (
            assert_msg_template.format(
                key=result_per_page_key,
                description='является число не менее 5'
            )
        )

        sort_by_key = 'sort_by'
        expected_sort_by_val = 'date'
        assert student_params[sort_by_key] == expected_sort_by_val, (
            assert_msg_template.format(
                key=sort_by_key,
                description=f'является `{expected_sort_by_val}`'
            )
        )

    def test_bot_init_not_global(self, homework_module):
        for var in homework_module.__dict__:
            assert not isinstance(
                getattr(homework_module, var),
                telegram.Bot
            ), (
                'Убедитесь, что бот инициализируется только в функции '
                '`main()`.'
            )

    def test_logger(self, homework_module):
        assert hasattr(homework_module, 'logging'), (
            'Убедитесь, что логирование бота настроено.'
        )
        logging_config_pattern = re.compile(
            r'(logging\.basicConfig ?\()'
        )
        hw_source = (
            utils.get_clean_source_code(inspect.getsource(homework_module))
        )
        logging_config = re.search(logging_config_pattern, hw_source)
        get_logger_pattern = re.compile(r'getLogger ?\(')
        logger = re.search(get_logger_pattern, hw_source)
        assert any((logging_config, logger)), (
            'Убедитесь, что логирование бота настроено с помощью '
            'функции `logging.basicConfig()` или класса `Logger` '
            '(`logging.getLogger()`).'
        )

    def test_request_call(self, monkeypatch, homework_module):
        func_name = 'get_api_answer'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )

        def check_request_call(url, **kwargs):
            expected_url = (
                'https://api.adzuna.com/v1/api/jobs/'
            )
            assert url.startswith(expected_url), (
                'Проверьте адрес, на который отправляются запросы.'
            )
            assert 'params' in kwargs, (
                'Проверьте, что в запросе переданы параметры `params`.'
            )
            assert getattr(homework_module, 'PARAMS') == kwargs['params'], (
                'Проверьте, что в качестве параметров запроса в функцию '
                '`requests.get()` передан словарь `PARAMS`.'
            )

        monkeypatch.setattr(requests, 'get', check_request_call)
        try:
            homework_module.get_api_answer()
        except AssertionError:
            raise
        except Exception:
            pass

    def test_get_api_answers(self, monkeypatch, homework_module):
        func_name = 'get_api_answer'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )

        def mock_response_get(*args, **kwargs):
            return utils.MockResponseGET(*args, **kwargs)

        monkeypatch.setattr(requests, 'get', mock_response_get)

        result = homework_module.get_api_answer()
        assert isinstance(result, dict), (
            f'Проверьте, что функция `{func_name}` возвращает словарь.'
        )

    @pytest.mark.parametrize('response', NOT_OK_RESPONSES.values())
    def test_get_not_200_status_response(self, monkeypatch, response,
                                         homework_module):
        func_name = 'get_api_answer'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )

        monkeypatch.setattr(requests, 'get', response)
        try:
            homework_module.get_api_answer()
        except Exception:
            pass
        else:
            raise AssertionError(
                f'Убедитесь, что в функции `{func_name}` обрабатывается '
                'ситуация, когда API домашки возвращает код, отличный от 200.'
            )

    def test_get_api_answer_with_request_exception(self, monkeypatch,
                                                   homework_module):
        func_name = 'get_api_answer'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )

        def mock_request_get_with_exception(*args, **kwargs):
            raise requests.RequestException('Something wrong')

        monkeypatch.setattr(requests, 'get', mock_request_get_with_exception)
        try:
            homework_module.get_api_answer()
        except requests.RequestException as e:
            raise AssertionError(
                f'Убедитесь, что в функции `{func_name}` обрабатывается '
                'ситуация, когда при запросе к API возникает исключение '
                '`requests.RequestException`.'
            ) from e
        except Exception:
            pass

    def test_parse_vacancy_with_expected_data(self, homework_module):
        func_name = 'parse_vacancy'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )

        test_data = utils.MockResponseGET().json()['results'][0]
        result = homework_module.parse_vacancy(test_data)
        assert isinstance(result, str), (
            f'Проверьте, что функция `{func_name}` возвращает строку.'
        )
        expected_info_map = {
            'название компании': test_data['company']['display_name'],
            'локацию, в которой открыта вакансия': (
                test_data['location']['display_name']
            ),
            'название должности': test_data['title'],
            'ссылку на вакансию': test_data['redirect_url']
        }
        for info_type, info in expected_info_map.items():
            assert info in result, (
                'Убедитесь, что строка, формируемая в результате исполнения '
                f'функции `{func_name}`, содержит {info_type}.'
            )

    @pytest.mark.parametrize('missing_key',
                             ['company', 'location', 'title', 'redirect_url'])
    def test_parse_vacancy_no_homework_name_key(self, homework_module,
                                                missing_key):
        func_name = 'parse_vacancy'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )
        vacancy_data = {
            'company': {'display_name': 'Fake Company'},
            'location': {'display_name': 'Edinburgh, Scotland'},
            'title': 'Python Engineer',
            'redirect_url': 'https://www.adzuna.co.uk/continuation'
        }
        vacancy_data.pop(missing_key)
        try:
            homework_module.parse_vacancy(vacancy_data)
        except KeyError as e:
            if repr(e) == f"KeyError('{missing_key}')":
                raise AssertionError(
                    f'Убедитесь, что функция `{func_name}` выбрасывает '
                    'исключение с понятным текстом ошибки, когда в ответе '
                    f'API нет ключа `{missing_key}`.'
                )
        except Exception:
            pass
        else:
            raise AssertionError(
                f'Убедитесь, что функция `{func_name}` выбрасывает '
                'исключение, когда в ответе API домашки нет ключа '
                f'`{missing_key}`.'
            )

    def test_check_response(self, homework_module):
        func_name = 'check_response'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )

        valid_response = utils.MockResponseGET().json()
        try:
            homework_module.check_response(valid_response)
        except Exception as e:
            raise AssertionError(
                'Убедитесь, что при корректном ответе API функция '
                f'`{func_name}` не вызывает исключений.'
            ) from e

    @pytest.mark.parametrize('response', INVALID_RESPONSES.values())
    def test_check_invalid_response(self, response, homework_module):
        func_name = 'check_response'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )

        if response.defected_key:
            try:
                homework_module.check_response(response.data)
            except KeyError as e:
                if repr(e) == f"KeyError('{response.defected_key}')":
                    raise AssertionError(
                        f'Убедитесь, что функция `{func_name}` выбрасывает '
                        'исключение, если в ответе API домашки нет ключа '
                        f'`{response.defected_key}`.'
                    ) from e
            except Exception:
                pass
            else:
                raise AssertionError(
                    f'Убедитесь, что функция `{func_name}` выбрасывает '
                    'исключение, если в ответе API домашки нет ключа '
                    f'`{response.defected_key}`.'
                )
        else:
            assert_message = (
                f'Убедитесь, что функция `{func_name}` выбрасывает исключение '
                '`TypeError`, если в ответе API домашки '
                'под ключом `results` данные приходят не в виде списка.'
            )
            if isinstance(response.data, list):
                assert_message = (
                    f'Убедитесь, что функция `{func_name}` выбрасывает '
                    'исключение `TypeError`, если в ответе API '
                    'структура данных не соответствует ожиданиям: например, '
                    'получен список вместо ожидаемого словаря.'
                )
            try:
                homework_module.check_response(response.data)
            except TypeError:
                pass
            except Exception:
                raise AssertionError(assert_message)
            else:
                raise AssertionError(assert_message)

    def test_send_message(self, monkeypatch, random_message,
                          caplog, homework_module):
        monkeypatch.setattr(homework_module, 'API_ID', 'id4api')
        monkeypatch.setattr(homework_module, 'API_KEY', 's0m3-api-k3y')
        monkeypatch.setattr(homework_module, 'TELEGRAM_TOKEN', '1234:abcdefg')
        monkeypatch.setattr(homework_module, 'TELEGRAM_CHAT_ID', '12345')

        func_name = 'send_message'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )

        bot = get_mock_telegram_bot(monkeypatch, random_message)

        with utils.check_logging(caplog, level=logging.DEBUG, message=(
                'Убедитесь, что при успешной отправке сообщения в Telegram '
                'событие логируется с уровнем `DEBUG`.'
        )):
            homework_module.send_message(bot, 'Test_message_check')
            assert bot.chat_id, (
                'Проверьте, что при отправке сообщения бота '
                'передан параметр `chat_id`.'
            )
            assert bot.text, (
                'Проверьте, что при отправке сообщения бота '
                'передан параметр `text`.'
            )
            assert bot.is_message_sent, (
                'Убедитесь, что для отправки сообщения в Telegram применён '
                'метод бота `send_message`.'
            )

    def test_bot_initialized_in_main(self, homework_module):
        func_name = 'main'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )

        main_source = utils.get_clean_source_code(
            inspect.getsource(homework_module.main)
        )
        bot_init_pattern = re.compile(
            r'(\w* ?= ?)((telegram\.)?Bot\( *[\w=_\-\'\"]* *\))'
        )
        search_result = re.search(bot_init_pattern, main_source)
        assert search_result, (
            'Убедитесь, что бот инициализируется только в функции `main()`.'
        )

        bot_init_with_token_pattern = re.compile(
            r'Bot\( *token *= *TELEGRAM_TOKEN *\)'
        )
        assert re.search(bot_init_with_token_pattern, main_source), (
            'Убедитесь, что при создании бота в него передан токен: '
            '`token=TELEGRAM_TOKEN`.'
        )

    def mock_main(self, monkeypatch, random_message, homework_module,
                  mock_bot=True, response_data=None):
        """
        Mock all functions inside main() which need environment vars to work
        correctly.
        """
        monkeypatch.setattr(homework_module, 'API_ID', 'id4api')
        monkeypatch.setattr(homework_module, 'API_KEY', 's0m3-api-k3y')
        monkeypatch.setattr(homework_module, 'TELEGRAM_TOKEN', '1234:abcdefg')
        monkeypatch.setattr(homework_module, 'TELEGRAM_CHAT_ID', '12345')

        func_name = 'main'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )

        main_source = utils.get_clean_source_code(
            inspect.getsource(homework_module.main)
        )

        time_sleep_pattern = re.compile(
            r'(\# *)?(time\.sleep\( *[\w\d=_\-\'\"]* *\))'
        )
        search_result = re.search(time_sleep_pattern, main_source)
        assert search_result, (
            'Убедитесь, что в `main()` применена функция `time.sleep()`.'
        )

        def sleep_to_interrupt(secs):
            caller = inspect.stack()[1].function
            if caller != 'main':
                old_sleep(secs)
                return
            assert secs == 600, (
                'Убедитесь, что повторный запрос к API домашки отправляется '
                'через 10 минут: `time.sleep(RETRY_PERIOD)`.'
            )
            raise utils.BreakInfiniteLoop('break')

        monkeypatch.setattr(time, 'sleep', sleep_to_interrupt)
        if mock_bot:
            def mock_telegram_bot(random_message=random_message, *args,
                                  **kwargs):
                return utils.MockTelegramBot(*args, message=random_message,
                                             **kwargs)

            monkeypatch.setattr(telegram, 'Bot', mock_telegram_bot)

        func_name = 'get_api_answer'
        utils.check_function(
            homework_module,
            func_name,
            self.HOMEWORK_FUNC_WITH_PARAMS_QTY[func_name]
        )

        mock_response_get_with_new_status = (
            create_mock_response_get_with_custom_status_and_data(
                http_status=HTTPStatus.OK,
                data=response_data
            )
        )
        monkeypatch.setattr(
            requests,
            'get',
            mock_response_get_with_new_status
        )
        if platform.system() != 'Windows':
            homework_module.main = utils.with_timeout(homework_module.main)

    def test_main_without_env_vars_raise_exception(
            self, caplog, monkeypatch, random_message, homework_module
    ):
        self.mock_main(monkeypatch, random_message, homework_module)
        monkeypatch.setattr(homework_module, 'API_ID', None)
        monkeypatch.setattr(homework_module, 'API_KEY', None)
        monkeypatch.setattr(homework_module, 'TELEGRAM_TOKEN', None)
        monkeypatch.setattr(homework_module, 'TELEGRAM_CHAT_ID', None)
        with utils.check_logging(caplog, level=logging.CRITICAL, message=(
                'Убедитесь, что при отсутствии обязательных переменных '
                'окружения событие логируется с уровнем `CRITICAL`.'
        )):
            try:
                homework_module.main()
            except utils.BreakInfiniteLoop:
                raise AssertionError(
                    'Убедитесь, что при запуске бота без переменных окружения '
                    'программа принудительно останавливается.'
                )
            except (Exception, SystemExit):
                pass

    def test_main_send_request_to_api(self, monkeypatch, random_message,
                                      caplog, homework_module):
        self.mock_main(monkeypatch, random_message, homework_module)

        with caplog.at_level(logging.WARN):
            try:
                homework_module.main()
            except utils.BreakInfiniteLoop:
                log_record = [
                    record for record in caplog.records
                    if record.message == utils.MockResponseGET.CALLED_LOG_MSG
                ]
                assert log_record, (
                    'Убедитесь, что бот использует функцию `requests.get()` '
                    'для отправки запроса к API домашки.'
                )

    def test_main_check_response_is_called(self, monkeypatch, random_message,
                                           caplog, homework_module):
        self.mock_main(monkeypatch, random_message, homework_module)
        func_name = 'check_response'
        expecred_data = utils.MockResponseGET().json()
        log_msg = 'Call check_response'
        no_response_assert_msg = (
            f'Убедитесь, что в функцию `{func_name}` передан ответ API.'
        )

        def mock_check_response(response=None):
            if response != expecred_data:
                raise SystemExit(no_response_assert_msg)
            logging.warning(log_msg)

        monkeypatch.setattr(
            homework_module,
            func_name,
            mock_check_response
        )
        with caplog.at_level(logging.WARN):
            try:
                homework_module.main()
            except SystemExit:
                raise AssertionError(no_response_assert_msg)
            except utils.BreakInfiniteLoop:
                log_records = [
                    record for record in caplog.records
                    if record.message in (log_msg, no_response_assert_msg)
                ]
                assert log_records, (
                    'Убедитесь, что для проверки ответа API бот использует '
                    f'функцию `{func_name}`.'
                )

    def test_main_send_message_with_new_vacancy(self, monkeypatch,
                                                random_message,
                                                caplog, homework_module):
        self.mock_main(monkeypatch, random_message, homework_module,)

        vacancy_title = utils.MockResponseGET().json()['results'][0]['title']

        def mock_send_message(bot, message=''):
            logging.warning(message)

        monkeypatch.setattr(homework_module, 'send_message', mock_send_message)
        with caplog.at_level(logging.WARN):
            try:
                homework_module.main()
            except utils.BreakInfiniteLoop:
                log_record = [
                    record.message for record in caplog.records
                    if vacancy_title in record.message
                ]
                assert log_record, (
                    'Убедитесь, что при наличии в ответе новой вакансии '
                    'бот отправляет в Telegram сообщение.с информацией о ней.'
                )
            except (Exception, SystemExit) as e:
                raise AssertionError(
                    f'Вызов функции `main` завершился ошибкой: {e}'
                ) from e

    def test_main_send_message_with_telegram_exception(self, monkeypatch,
                                                       random_message,
                                                       caplog,
                                                       homework_module):
        self.mock_main(
            monkeypatch, random_message, homework_module, mock_bot=False
        )

        class MockedBotWithException(utils.MockTelegramBot):
            def send_message(self, *args, **kwargs):
                raise telegram.error.TelegramError('Something wrong')

        monkeypatch.setattr(telegram, 'Bot', MockedBotWithException)

        with utils.check_logging(caplog, level=logging.ERROR, message=(
                'Убедитесь, что ошибка отправки сообщения в Telegram '
                'логируется с уровнем `ERROR`.'
        )):
            try:
                homework_module.main()
            except utils.BreakInfiniteLoop:
                pass
            except (Exception, SystemExit) as e:
                raise AssertionError(
                    'Убедитесь, что бот не останавливает работу при '
                    'возникновении ошибки отправки сообщения в Телеграм.'
                ) from e

    def test_docstrings(self, homework_module):
        for func in self.HOMEWORK_FUNC_WITH_PARAMS_QTY:
            utils.check_docstring(homework_module, func)


if __name__ == '__main__':
    pytest.main()
