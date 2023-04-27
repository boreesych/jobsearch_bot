class NotForSendingError(Exception):
    """Базовый класс для исключений, которые не отправляются в Telegram."""


class UnexpectedAPIResponseError(NotForSendingError):
    """Исключение при получении ответа не соответствующего ожидаемому."""


class NotOkAPIResponseCodeError(Exception):
    """Исключение когда код ответа сервера != 200."""
