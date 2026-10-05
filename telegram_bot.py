"""
Telegram Automation Bot with Instant Order Notifications
Library: python-telegram-bot v20+
Run on: Pydroid 3 (Android)

Install first (Pydroid 3 -> menu -> Pip -> search "python-telegram-bot"):
    pip install python-telegram-bot
"""

import html
import logging
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
from telegram.request import HTTPXRequest

# ============================================================
# CONFIGURATION: edit everything here, no database needed
# ============================================================
BOT_TOKEN = "8796056848:AAGS9dmXOSqB082LnPTCpAEAABy6KvyeaM0"  # <-- paste your token from BotFather

# Your personal Telegram Chat ID (numbers only, e.g. 123456789).
# Get it by messaging @userinfobot on Telegram.
# IMPORTANT: open your bot and press /start once, or it can't message you.
OWNER_CHAT_ID = 8931434283

# Your UTC offset for timestamps (Philippines = 8, UTC = 0, etc.)
UTC_OFFSET_HOURS = 8

STORE_NAME = "My Store"

PRODUCTS = {
    "Item 1": 100,
    "Item 2": 250,
    "Item 3": 500,
    "Item 4": 750,
}
CURRENCY = "₱"

PAYMENT_METHODS = {
    "GCash": {"name": "Juan Dela Cruz", "number": "0912 345 6789"},
    "PayMaya": {"name": "Juan Dela Cruz", "number": "0998 765 4321"},
}

CONTACT = {
    "telegram_username": "your_username",  # without the @
    "phone": "0912 345 6789",
}
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Fixed list so button callbacks can use short indexes
PRODUCT_LIST = list(PRODUCTS.items())


# ---------- Helpers ----------
def now_text() -> str:
    tz = timezone(timedelta(hours=UTC_OFFSET_HOURS))
    return datetime.now(tz).strftime("%Y-%m-%d %I:%M:%S %p")


def customer_label(user) -> str:
    """Return @username if available, otherwise first name (HTML-safe)."""
    if user.username:
        return f"@{html.escape(user.username)}"
    return html.escape(user.first_name or "Unknown")


# ---------- Text builders ----------
def welcome_text(first_name: str) -> str:
    return (
        f"👋 Hello, <b>{html.escape(first_name)}</b>!\n\n"
        f"Welcome to <b>{STORE_NAME}</b>.\n"
        "Please choose an option below:"
    )


def products_text() -> str:
    lines = ["📦 <b>Products / Menu</b>\n"]
    for item, price in PRODUCT_LIST:
        lines.append(f"• {item} — <b>{CURRENCY}{price:,}</b>")
    lines.append("\n👇 Tap an item below to place your order.")
    return "\n".join(lines)


def payment_text() -> str:
    lines = ["💳 <b>Payment Methods</b>\n"]
    for method, info in PAYMENT_METHODS.items():
        lines.append(
            f"<b>{method}</b>\n"
            f"Name: {info['name']}\n"
            f"Number: <code>{info['number']}</code>\n"
        )
    lines.append("📸 Please send your proof of payment after paying.")
    return "\n".join(lines)


def contact_text() -> str:
    return (
        "📞 <b>Contact Owner</b>\n\n"
        f"Telegram: @{CONTACT['telegram_username']}\n"
        f"Phone: {CONTACT['phone']}"
    )


def order_confirmation_text(item: str, price: int) -> str:
    return (
        "✅ <b>Order sent!</b>\n\n"
        f"Item: <b>{item}</b>\n"
        f"Price: <b>{CURRENCY}{price:,}</b>\n\n"
        "The owner has been notified and will contact you shortly.\n"
        "You can check 💳 Payment Methods to pay in the meantime."
    )


# ---------- Keyboards ----------
def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📦 Products / Menu", callback_data="products")],
        [InlineKeyboardButton("💳 Payment Methods", callback_data="payment")],
        [InlineKeyboardButton("📞 Contact Owner", callback_data="contact")],
    ]
    return InlineKeyboardMarkup(keyboard)


def products_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"🛒 {item} — {CURRENCY}{price:,}",
                callback_data=f"buy:{index}",
            )
        ]
        for index, (item, price) in enumerate(PRODUCT_LIST)
    ]
    rows.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def back_keyboard(extra_buttons=None) -> InlineKeyboardMarkup:
    rows = []
    if extra_buttons:
        rows.append(extra_buttons)
    rows.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def after_order_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Payment Methods", callback_data="payment")],
            [InlineKeyboardButton("📦 Order Something Else", callback_data="products")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")],
        ]
    )


# ---------- Owner notification ----------
async def notify_owner(context: ContextTypes.DEFAULT_TYPE, user, item: str, price: int) -> bool:
    """Send an instant order alert to the owner. Returns True on success."""
    text = (
        "🔔 <b>New Order Received!</b>\n\n"
        f"👤 Customer: {customer_label(user)}\n"
        f"🆔 User ID: <code>{user.id}</code>\n"
        f"📦 Item: <b>{html.escape(item)}</b>\n"
        f"💰 Price: <b>{CURRENCY}{price:,}</b>\n"
        f"🕒 Time: {now_text()}\n\n"
        f'<a href="tg://user?id={user.id}">Open chat with customer</a>'
    )
    try:
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
        )
        return True
    except TelegramError as exc:
        logger.error("Could not notify owner: %s", exc)
        return False


# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        welcome_text(user.first_name or "there"),
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # stops the loading spinner on the button

    data = query.data

    if data == "products":
        text, markup = products_text(), products_keyboard()

    elif data == "payment":
        text, markup = payment_text(), back_keyboard()

    elif data == "contact":
        link_button = [
            InlineKeyboardButton(
                "💬 Message on Telegram",
                url=f"https://t.me/{CONTACT['telegram_username']}",
            )
        ]
        text, markup = contact_text(), back_keyboard(link_button)

    elif data.startswith("buy:"):
        try:
            item, price = PRODUCT_LIST[int(data.split(":")[1])]
        except (ValueError, IndexError):
            await query.answer("Item not found.", show_alert=True)
            return

        sent = await notify_owner(context, query.from_user, item, price)
        if sent:
            text, markup = order_confirmation_text(item, price), after_order_keyboard()
        else:
            text = (
                "⚠️ Your order could not be delivered automatically.\n"
                "Please contact the owner directly."
            )
            link_button = [
                InlineKeyboardButton(
                    "💬 Message on Telegram",
                    url=f"https://t.me/{CONTACT['telegram_username']}",
                )
            ]
            markup = back_keyboard(link_button)

    else:  # "menu"
        text = welcome_text(query.from_user.first_name or "there")
        markup = main_menu_keyboard()

    await query.edit_message_text(
        text=text,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Error while handling an update:", exc_info=context.error)


# ---------- Main ----------
def main() -> None:
    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        print("⚠️ Please replace YOUR_BOT_TOKEN with your real token first.")
        return

    # Custom timeouts for slow / unstable mobile networks
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )
    # Separate request object for long-polling (getUpdates)
    updates_request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(updates_request)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    print("🤖 Bot is running... Press Stop in Pydroid to end it.")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        bootstrap_retries=-1,  # keep retrying if the first connection times out
    )


if __name__ == "__main__":
    main()
