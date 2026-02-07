import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
logger = logging.getLogger(__name__)


def send_tg_message(chat_id, text) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    try:
        response = requests.post(url, json=payload, timeout=5)
    except requests.RequestException:
        logger.exception("Telegram send failed for chat_id=%s", chat_id)
        return False

    if response.status_code != 200:
        logger.warning("Telegram send failed chat_id=%s status=%s body=%s", chat_id, response.status_code, response.text)
        return False

    return True

from django.contrib.auth.models import Group

def get_telegram_ids_for_group(group_name):
    try:
        group_users = Group.objects.get(name=group_name).user_set.all()
        return [
            user.telegram_id
            for user in group_users
            if user.telegram_id
        ]
    except Group.DoesNotExist:
        return []


def generate_order_details(order):
    details = f"{order.model.name}, {order.color.name}"
    additional = []

    if order.embroidery:
        additional.append("Вишивка")
    if order.urgent:
        additional.append("Терміново")
    if order.etsy:
        additional.append("Etsy")
    if order.comment:
        additional.append(f"\n{order.comment}")

    if additional:
        details += "\nДеталі: " + ", ".join(additional)

    return details
