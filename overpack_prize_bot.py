import random
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import logging

API_TOKEN = '7852208865:AAE8kHFPEPid7YUu52dYh1X5voV_d-aaR1o'
CHANNEL_USERNAME = '@OverpackTG'
ADMIN_ID = 859439617
ADMIN_TELEGRAM = '@OverpackTG'  # Телеграм админа/продавца

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

allowed_users = set()
last_spin_time = {}  # словарь для хранения последнего времени крутки пользователя

spin_inline_keyboard = InlineKeyboardMarkup().add(
    InlineKeyboardButton("🎰 Крутить колесо", callback_data="spin")
)

request_access_keyboard = InlineKeyboardMarkup().add(
    InlineKeyboardButton("⏩ Хочу крутить", callback_data="request_access")
)

# Настройки вероятности выпадения призов
prizes = [
    ("🔥 Уголь", 35),
    ("💸 Скидка 5% на следующую покупку", 30),
    ("🍬 Табак на выбор", 20),
    ("❌ Пусто", 10),
    ("🎲 Редкий приз", 5)
]

prize_list = [prize for prize, weight in prizes for _ in range(weight)]

async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ('member', 'creator', 'administrator')
    except:
        return False

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_id = message.from_user.id

    photo_path = 'Приветсвие.png'
    caption = (
        "🎉 <b>Ну что, дружище, готов испытать удачу?</b>\n\n"
        "Жми кнопку «⏩ Хочу крутить», и если продавец сегодня в духе — сразу получишь одобрение! 😉\n\n"
        "💡 <i>P.S. Только подписчики нашего канала @OverpackTG имеют право крутить колесо.</i>\n"
        "Если ты ещё не с нами — быстренько подпишись и проверяй подписку кнопкой ниже.👇"
    )

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("⏩ Хочу крутить", callback_data="request_access"),
        InlineKeyboardButton("📩 Проверить подписку", callback_data="check_sub")
    )

    with open(photo_path, 'rb') as photo:
        await bot.send_photo(chat_id=user_id, photo=photo, caption=caption, parse_mode='HTML', reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "request_access")
async def handle_request_access(callback_query: types.CallbackQuery):
    user = callback_query.from_user
    user_id = user.id
    if user_id in allowed_users:
        return await callback_query.answer("Ты уже в списке!")

    text = (
        "📩 Запрос доступа к крутке\n\n"
        f"👤 Пользователь: @{user.username or 'Без ника'}\n"
        f"🆔 ID: {user_id}"
    )
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Разрешить", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"deny_{user_id}")
    )
    await bot.send_message(chat_id=ADMIN_ID, text=text, reply_markup=keyboard)
    await bot.send_message(user_id, "📬 Запрос отправлен админу. Жди одобрения 🙌")
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve_user(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    allowed_users.add(user_id)
    await bot.send_message(user_id, "✅ Админ одобрил — теперь ты можешь крутить колесо! 🎡", reply_markup=spin_inline_keyboard)
    await callback_query.answer("Пользователь одобрен ✅")

@dp.callback_query_handler(lambda c: c.data.startswith("deny_"))
async def deny_user(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    await bot.send_message(user_id, "❌ Доступ не одобрен. Попробуй позже или уточни у продавца.")
    await callback_query.answer("Пользователь отклонён ❌")

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_subscription(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if await is_subscribed(user_id):
        await bot.send_message(user_id, "✅ Подписка подтверждена! Нажми кнопку для запроса доступа.", reply_markup=request_access_keyboard)
    else:
        await callback_query.answer("❌ Подпишись на канал, чтобы продолжить", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "spin")
async def spin_wheel(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in allowed_users:
        return await callback_query.answer("Ты пока не в списке. Запроси доступ через /start", show_alert=True)

    # Проверка на ограничение 24 часа
    current_time = datetime.now()
    if user_id in last_spin_time and current_time - last_spin_time[user_id] < timedelta(hours=24):
        next_spin = last_spin_time[user_id] + timedelta(hours=24)
        wait_time = next_spin - current_time
        hours, remainder = divmod(wait_time.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return await bot.send_message(user_id, f"⏳ Подожди еще {hours} ч. {minutes} мин. до следующей крутки!")

    last_spin_time[user_id] = current_time

    await bot.send_message(user_id, "🎡 Крутим колесо...\n🕓 3...\n🕓 2...\n🕓 1...\n🥁 ...")
    await asyncio.sleep(3)

    prize = random.choice(prize_list)
    if prize == "❌ Пусто":
        await bot.send_message(user_id, "🤷‍♂️ Увы, сегодня без приза. Повезёт в следующий раз!")
    elif prize == "🎲 Редкий приз":
        await bot.send_message(user_id, f"🎲 Ты выиграл редкий приз! Напиши продавцу {ADMIN_TELEGRAM} и узнай, что тебе причитается 😉")
    else:
        await bot.send_message(user_id, f"🎁 Тебе выпало: {prize}\nПокажи это продавцу и получи приз! 🎉")

    log_text = f"🎡 Крутка:\n👤 @{callback_query.from_user.username or 'Без ника'}\n🆔 ID: {user_id}\n🎁 Приз: {prize}\n🕒 Время: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
    await bot.send_message(chat_id=ADMIN_ID, text=log_text)
    await callback_query.answer()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
