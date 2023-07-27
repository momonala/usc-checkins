import logging

import requests

from usc.values import telegram_api_token, telegram_chat_id

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def send_to_telegram(msg: str):
    telegrap_api_uri = f'https://api.telegram.org/bot{telegram_api_token}/sendMessage'
    resp = requests.post(
        telegrap_api_uri, json={'chat_id': telegram_chat_id, 'text': msg, 'parse_mode': 'Markdown'}
    )
    logger.info("Sent message to Telegram") if resp.status_code == 200 else logger.error(resp.text)
