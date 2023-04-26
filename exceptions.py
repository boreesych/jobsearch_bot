class NotForSendingError(Exception):
    """Базовый класс для исключений, которые не отправляются в Telegram."""
    pass


class TelegramError(NotForSendingError):
    """Исключение при неудачной попытке отправки сообщения в Telegram."""
    pass


class UnexpectedAPIResponseError(NotForSendingError):
    """Исключение при получении ответа не соответствующего ожидаемому."""
    pass


class NotOkAPIResponseCodeError(Exception):
    """Исключение когда код ответа сервера != 200."""
    pass


class ConnectionError(Exception):
    """Исключение при ошибке при подключению к серверу."""
    pass