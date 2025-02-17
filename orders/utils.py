import requests
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Retrieve TELEGRAM_BOT_TOKEN from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


def send_tg_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    response = requests.post(url, json=payload)

    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")

from django.contrib.auth.models import Group

# Helper function to fetch Telegram IDs for a group
def get_telegram_ids_for_group(group_name):
    try:
        group_users = Group.objects.get(name=group_name).user_set.all()
        return [
            user.telegram_id
            for user in group_users
            if user.telegram_id  # Only include non-empty Telegram IDs
        ]
    except Group.DoesNotExist:
        return []


# Helper function to generate order details
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

