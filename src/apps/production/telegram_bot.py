import os

import django
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Please define it in your .env file.")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.production.domain.status import STATUS_DONE  # noqa: E402
from apps.production.models import ProductionOrder  # noqa: E402


# Command handler functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    await update.message.reply_text("Welcome! I'm your bot. Use commands to interact with me!")


async def not_finished_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /not_finished_orders command to retrieve unfinished orders from the database."""
    try:
        unfinished_orders = ProductionOrder.objects.exclude(status=STATUS_DONE).select_related(
            "product", "variant", "variant__color"
        )
        if unfinished_orders.exists():
            response = "Here are your unfinished orders:\n"
            for order in unfinished_orders:
                response += (
                    f"- Order ID: {order.id}, "
                    f"Status: {order.get_status_display()}, "
                    f"Created At: {order.created_at}\n"
                )
        else:
            response = "You have no unfinished orders!"
    except Exception as e:
        response = f"An error occurred: {str(e)}"

    await update.message.reply_text(response)


# Main function to create the bot application
def main() -> Application:
    """Create the Telegram bot application."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("not_finished_orders", not_finished_orders))

    return application
