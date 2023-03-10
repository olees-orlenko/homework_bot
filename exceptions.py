class GlobalVariableError(Exception):
    """Некорретные переменные окружения."""


class SendMessageError(Exception):
    """Ошибка при отправке сообщения."""


class ApiAnswerError(Exception):
    """Некорректный ответ от API."""


class ParseStatusError(Exception):
    """Ошибка в функции parse_status."""
