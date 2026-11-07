import asyncio
import logging
import os
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.types import BotStarted, MessageCreated, MessageCallback
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton
from maxapi.context import MemoryContext, StatesGroup, State

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- Конфигурация ---
# Токен
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Временное хранилище (для MVP) ---
user_data = {}

# --- Состояния для регистрации ---
class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_school = State()
    waiting_for_subject = State()

# --- Клавиатуры (через Builder) ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="📋 Рутина (планы/напоминания)", payload="routine"))
    builder.row(CallbackButton(text="🔍 Поиск материалов", payload="search"))
    builder.row(CallbackButton(text="💬 Общение (шаблоны)", payload="communication"))
    builder.row(CallbackButton(text="📊 Отчёты", payload="reports"))
    builder.row(CallbackButton(text="👤 Мой профиль", payload="profile"))
    return builder.as_markup()

def get_back_menu():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🔙 В главное меню", payload="main_menu"))
    return builder.as_markup()

# ==========================================
# 1. ОБРАБОТЧИК ЗАПУСКА БОТА (bot_started)
# ==========================================
@dp.bot_started()
async def on_bot_started(event: BotStarted):
    user_id = event.user.user_id
    
    if user_id in user_data:
        await event.bot.send_message(
            chat_id=event.chat_id,
            text=f"С возвращением, {user_data[user_id]['name']}!",
            attachments=[get_main_menu()]
        )
        return

    await event.bot.send_message(
        chat_id=event.chat_id,
        text="👋 Привет! Я ПедПульт — ваш помощник в рутине.\n"
             "Давайте познакомимся. Как вас зовут?"
    )
    
    await dp.fsm.set_state(
        chat_id=event.chat_id,
        user_id=user_id,
        state=Registration.waiting_for_name
    )

# ==========================================
# 2. ОБРАБОТЧИКИ РЕГИСТРАЦИИ (FSM)
# ==========================================
@dp.message_created(Registration.waiting_for_name)
async def process_name(event: MessageCreated, context: MemoryContext):
    await context.update_data(name=event.message.body.text)
    await event.message.answer("Отлично! В какой школе (техникуме) вы работаете?")
    await context.set_state(Registration.waiting_for_school)

@dp.message_created(Registration.waiting_for_school)
async def process_school(event: MessageCreated, context: MemoryContext):
    await context.update_data(school=event.message.body.text)
    await event.message.answer("Какой предмет вы преподаёте?")
    await context.set_state(Registration.waiting_for_subject)

@dp.message_created(Registration.waiting_for_subject)
async def process_subject(event: MessageCreated, context: MemoryContext):
    # Используем get_ids() для получения идентификаторов
    chat_id, user_id = event.get_ids()
    
    data = await context.get_data()
    
    # Сохраняем в "базу"
    user_data[user_id] = {
        "name": data.get("name"),
        "school": data.get("school"),
        "subject": event.message.body.text
    }
    
    await context.clear()
    await event.message.answer(
        f"✅ Регистрация завершена!\n"
        f"Имя: {user_data[user_id]['name']}\n"
        f"Школа: {user_data[user_id]['school']}\n"
        f"Предмет: {user_data[user_id]['subject']}\n\n"
        "Теперь вы можете пользоваться сервисом.",
        attachments=[get_main_menu()]
    )

# ==========================================
# 3. ОБРАБОТЧИК КНОПОК (CALLBACK)
# ==========================================
@dp.message_callback(F.callback.payload)
async def on_callback(event: MessageCallback):
    payload = event.callback.payload
    chat_id, user_id = event.get_ids()

    if payload == "main_menu":
        await event.answer()
        await bot.send_message(
            chat_id=chat_id,
            text="Главное меню. Выберите раздел:",
            attachments=[get_main_menu()]
        )
        return

    # Проверка регистрации для остальных действий
    if user_id not in user_data:
        await event.answer("Пожалуйста, сначала зарегистрируйтесь.")
        return

    # --- Модуль: Рутина ---
    if payload == "routine":
        await event.answer()
        await bot.send_message(
            chat_id=chat_id,
            text="📋 **Модуль «Рутина»**\n\n"
                 "Здесь вы можете:\n"
                 "• Сгенерировать план урока по шаблону\n"
                 "• Поставить напоминание о сдаче отчёта\n"
                 "• Заполнить документы автоматически\n\n"
                 "(В MVP это заглушка. Полная версия использует LLM для генерации текста)",
            attachments=[get_back_menu()]
        )

    # --- Модуль: Поиск ---
    elif payload == "search":
        await event.answer()
        await bot.send_message(
            chat_id=chat_id,
            text="🔍 **Модуль «Поиск материалов»**\n\n"
                 "Отправьте мне тему, и я найду подходящие материалы.\n"
                 "Фильтры: класс, предмет, тип файла (PDF/DOCX).\n\n"
                 "(В MVP это заглушка. Полная версия ищет по базе ФИПИ/МЭШ)",
            attachments=[get_back_menu()]
        )

    # --- Модуль: Общение ---
    elif payload == "communication":
        await event.answer()
        await bot.send_message(
            chat_id=chat_id,
            text="💬 **Модуль «Общение»**\n\n"
                 "Быстрые ответы-шаблоны для родителей и коллег.\n"
                 "Пересылка сообщений без переключения между чатами.\n\n"
                 "(В MVP это заглушка. Полная версия интегрируется с чатами MAX)",
            attachments=[get_back_menu()]
        )

    # --- Модуль: Отчёты ---
    elif payload == "reports":
        await event.answer()
        await bot.send_message(
            chat_id=chat_id,
            text="📊 **Модуль «Отчёты»**\n\n"
                 "Формирование отчёта в один клик.\n"
                 "Экспорт в PDF/DOCX.\n"
                 "Автоматический сбор данных из журнала.\n\n"
                 "(В MVP это заглушка. Полная версия генерирует документы)",
            attachments=[get_back_menu()]
        )

    # --- Профиль ---
    elif payload == "profile":
        await event.answer()
        info = user_data[user_id]
        await bot.send_message(
            chat_id=chat_id,
            text=f"👤 **Ваш профиль**\n\n"
                 f"Имя: {info['name']}\n"
                 f"Школа: {info['school']}\n"
                 f"Предмет: {info['subject']}",
            attachments=[get_back_menu()]
        )

# ==========================================
# 4. ОБРАБОТЧИК КОМАНДЫ /start
# ==========================================
@dp.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    """Обработка текстовой команды /start."""
    user_id = event.user.user_id
    
    if user_id in user_data:
        await event.message.answer(
            f"С возвращением, {user_data[user_id]['name']}!",
            attachments=[get_main_menu()]
        )
        return

    await event.message.answer(
        "👋 Привет! Я ПедПульт — ваш помощник в рутине.\n"
        "Давайте познакомимся. Как вас зовут?"
    )
    await dp.fsm.set_state(
        chat_id=event.chat_id,
        user_id=user_id,
        state=Registration.waiting_for_name
    )

# ==========================================
# 5. ЗАПУСК
# ==========================================
async def main():
    print("Бот ПедПульт запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())