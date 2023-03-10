import logging
import os
import time

from http import HTTPStatus
from typing import Union

import requests
import telegram

from dotenv import load_dotenv
from exceptions import (ApiAnswerError,
                        GlobalVariableError,
                        ParseStatusError,
                        SendMessageError,)


load_dotenv()

SENDING_MESSAGE = 'Отправка сообщения'
SUCCESSFUL_SENDING_MESSAGE = 'Сообщение успешно отправлено!'
SENDING_MESSAGE_ERROR = '{message}: {error}'
MISSING_GLOBAL_VARIABLE = '{message}: {token}'
API_ANSWER_ERROR = '{message}: {error}'
INCORRECT_STATUS_CODE = '{message}: {response.status_code}'
WRONG_DATA_TYPE = 'Неверный тип данных'
WRONG_KEY_TYPE = 'Отсутствие ожидаемых ключей в ответе API: {type}'
KEY_ABSENCE = 'Отсутствует ключ "homework_name"'
STATUS_ABSENCE = 'Отсутствие в ответе новых статусов'
WRONG_STATUS = 'Неожиданный статус домашней работы {homework_status}'
GLOBAL_VARIABLE_ERROR = 'Ошибка глобальной переменной'
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logger = logging.getLogger(__name__)


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    for token in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
        if token is None:
            logger.critical(MISSING_GLOBAL_VARIABLE.format(
                token=token,
                message='Отсутствует глобальная переменная',
            ))
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в телеграм."""
    try:
        logger.error(SENDING_MESSAGE)
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        raise SendMessageError(SENDING_MESSAGE_ERROR.format(
            error=error,
            message='Сбой при отправке сообщения',
        ))
    else:
        logger.debug(SUCCESSFUL_SENDING_MESSAGE)


def get_api_answer(timestamp: int) -> Union[dict, str]:
    """Делает запрос к API."""
    timestamp = timestamp or int(time.time())
    params = {'from_date': 0}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise ApiAnswerError(INCORRECT_STATUS_CODE.format(
                response=response.status_code,
                message='Некорректный статус код',
            ))
        return response.json()
    except Exception as error:
        raise ApiAnswerError(API_ANSWER_ERROR.format(
            error=error,
            message='Возникла ошибка'
        ))


def check_response(response: dict) -> list:
    """Проверяет ответ API."""
    if not isinstance(response, dict):
        raise TypeError(WRONG_DATA_TYPE.format(response))
    homeworks = response.get('homeworks')
    if isinstance(response, list):
        response = response[0]
    if not isinstance(homeworks, list):
        raise TypeError(WRONG_KEY_TYPE)
    homeworks = response.get('homeworks')
    return homeworks


def parse_status(homework: dict) -> str:
    """Возвращает статус работы."""
    if not isinstance(homework, dict):
        logger.error(TypeError)
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError(KEY_ABSENCE)
    if homework_status is None:
        logger.debug(STATUS_ABSENCE)
    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise ParseStatusError(WRONG_STATUS)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise GlobalVariableError(GLOBAL_VARIABLE_ERROR)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    send_message(bot, 'Бот заработал')
    logger.info('Бот заработал')
    previous_msg = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            timestamp = response.get(
                'current_date', int(time.time())
            )
            if homework:
                message = parse_status(homework[0])
            else:
                message = 'Ничего нового не произошло'
            if message != previous_msg:
                send_message(bot, message)
                previous_msg = message
            else:
                logger.info(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=('%(asctime)s, %(levelname)s, %(message)s, '
                '%(filename)s, %(funcName)s, %(lineno)d'
                ),
        handlers=[logging.FileHandler('homework.log', mode='w'),
                  logging.StreamHandler()])
    main()
