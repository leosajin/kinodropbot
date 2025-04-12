import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

TOKEN = "8062821479:AAEoD1lYcY62g2IRtib3agvtKv5m4JxnXI8"
GROUP_LINK = "https://t.me/kinodropx"
DATA_FILE = "films.json"
CHANNELS_FILE = "channels.json"

# Список разрешённых пользователей
ALLOWED_ADMINS = [740791071, 8007461575]

user_requests = {}
add_mode = {}

# ------------------- Работа с каналами -------------------

def load_channels():
    if not os.path.exists(CHANNELS_FILE):
        return []
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_channels(channels):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=2, ensure_ascii=False)

# ------------------- Работа с ID -------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ------------------- Команды -------------------

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Введите ID фильма, чтобы найти его.")

def handle_id(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_id in add_mode:
        if add_mode[user_id]["step"] == "id":
            add_mode[user_id]["film_id"] = text
            add_mode[user_id]["step"] = "link"
            update.message.reply_text("Теперь отправь ссылку на пост:")
        elif add_mode[user_id]["step"] == "link":
            film_id = add_mode[user_id]["film_id"]
            post_link = text
            data = load_data()
            data[film_id] = post_link
            save_data(data)
            update.message.reply_text(f"✅ Добавлено: {film_id} → {post_link}")
            del add_mode[user_id]
        return

    user_requests[user_id] = text
    send_subscription_prompt(update, context)

def send_subscription_prompt(update: Update, context: CallbackContext):
    channels = load_channels()
    buttons = [[InlineKeyboardButton(c["title"], url=f"https://t.me/{c['username'][1:]}")] for c in channels]
    buttons.append([InlineKeyboardButton("✅ Подписался", callback_data="check_subs")])

    update.message.reply_text(
        "👥 Чтобы получить ссылку на фильм, подпишись на каналы:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

def check_subscriptions(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    query.answer()

    channels = load_channels()
    not_subscribed = []

    # Добавляем только названия каналов
    for c in channels:
        try:
            member = context.bot.get_chat_member(c["username"], user.id)
            if member.status not in ["member", "administrator", "creator"]:
                not_subscribed.append(c["title"])  # Добавляем название канала
        except:
            not_subscribed.append(c["title"])  # Добавляем название канала

    if not_subscribed:
        query.edit_message_text(
            f"❗ Я не вижу подписки на:\n" + "\n".join(not_subscribed) + "\n\nПроверь и нажми ещё раз.",
            reply_markup=query.message.reply_markup
        )
        return

    film_id = user_requests.get(user.id)
    data = load_data()
    if film_id in data:
        post_link = data[film_id]
        button = [[InlineKeyboardButton("🎬 Перейти к фильму", url=post_link)]]
        query.edit_message_text(
            f"✅ Найден фильм с ID {film_id}!",
            reply_markup=InlineKeyboardMarkup(button)
        )
    else:
        query.edit_message_text("❌ Такого ID не найдено. Попробуй ввести другой.")

# ------------------- Админ-команды -------------------

def add_film_start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_ADMINS:
        update.message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return
    add_mode[user_id] = {"step": "id"}
    update.message.reply_text("🆔 Введи ID фильма:")

def set_channels(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_ADMINS:
        update.message.reply_text("⛔ У тебя нет доступа к этой команде.")
        return

    if not context.args:
        update.message.reply_text(
            "Напиши через пробел список каналов. Пример:\n`/setchannels @chan1 @chan2 @chan3`",
            parse_mode="Markdown"
        )
        return

    usernames = context.args
    new_channels = []
    for idx, username in enumerate(usernames, start=1):
        new_channels.append({
            "title": f"Канал {idx}",
            "username": username
        })

    save_channels(new_channels)

    msg = "\n".join([f"{c['title']}: {c['username']}" for c in new_channels])
    update.message.reply_text(f"✅ Каналы обновлены:\n{msg}")

# ------------------- Запуск -------------------

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", add_film_start))
    dp.add_handler(CommandHandler("setchannels", set_channels))
    dp.add_handler(CallbackQueryHandler(check_subscriptions, pattern="check_subs"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_id))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
