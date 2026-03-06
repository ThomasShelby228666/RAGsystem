import dotenv
import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

# Загрузка переменных окружения из файла .env
dotenv.load_dotenv()

# Настройка системы логирования
logging.basicConfig(
    filename = 'rag_bot.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    encoding = 'utf-8'
)

# Попытка импорта функции из RAG-системы
try:
    from rag_main import run_rag_query
    RAG_AVAILABLE = True
except ImportError as e:
    logging.error(f"Не удалось импортировать RAG-систему: {e}")
    RAG_AVAILABLE = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Обрабатывает команду /start - отправляет приветственное сообщение с клавиатурой.

    Args:
        update (Update): Объект с информацией об обновлении от Telegram.
        context (ContextTypes.DEFAULT_TYPE): Контекст выполнения обработчика.
    '''
    # Приветственное сообщение
    welcome_message = (
        "Таки шалом! ✡\n"
        "Я бот на основе RAG-системы, который может ответить на вопросы о языке программирования Python.\n"
        "Отправь мне свой вопрос и я постараюсь помочь с ним!\n"
        "Например: 'Какие есть типы данных в Python?'\n"
        "/help для получения дополнительной информации"
    )

    # Создание клавиатуры с кнопками
    keyboard = [
        ["/start", "/help"],
        ["/stop"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    # Приветственное сообщение
    await update.message.reply_text(welcome_message, reply_markup = reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает входящие текстовые сообщения и отправляет ответ от RAG-системы.

    Args:
        update (Update): Объект с информацией об обновлении от Telegram.
        context (ContextTypes.DEFAULT_TYPE): Контекст выполнения обработчика.

    """
    # Проверка доступности RAG-системы
    if not RAG_AVAILABLE:
        await update.message.reply_text('Таки извините, RAG-система таки временно недоступна.')
        return

    # Получение текста сообщения от пользователя и установка имени пользователя для логирования
    user_message = update.message.text
    user_name = 'Пользователь'

    logging.info(f"Новый запрос от {user_name}: {user_message}")

    # Отправляем уведомление "печатает..." в чат
    await update.message.chat.send_action(ChatAction.TYPING)

    # Обработка запроса
    try:
        # Вызываем функцию RAG-системы в отдельном потоке для избежания блокировки
        answer = await asyncio.get_event_loop().run_in_executor(None, run_rag_query, user_message)

        # Проверяем, что ответ получен и является строкой
        if not answer or not isinstance(answer, str):
            answer = 'Извините, не удалось сформулировать ответ на ваш вопрос.'

        logging.info(f'Ответ для {user_name} отправлен')

        # Отправляем ответ пользователю
        await update.message.reply_text(answer, disable_web_page_preview = True)

    # Если возникает любая ошибка при обработке запроса
    except Exception as e:
        logging.error(f'Ошибка при обработке запроса от {user_name}: {e}')
        error_message = 'Таки произошла ошибка при обработке вашего запроса. Таки попробуйте позже.'
        await update.message.reply_text(error_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Обрабатывает команду /help - отправляет справку по командам.

    Args:
        update (Update): Объект с информацией об обновлении от Telegram.
        context (ContextTypes.DEFAULT_TYPE): Контекст выполнения обработчика.

    '''
    # Создаем текст справки с описанием доступных команд
    help_text = (
        "/start - Начать работу с ботом\n"
        "/help - Показать справку\n"
        "/stop - Остановить работу бота\n"
        "Просто отправьте текстовый вопрос, и я отвечу на основе документации Python!"
    )
    await update.message.reply_text(help_text)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Обрабатывает команду /stop - отправляет сообщение о приостановке.

    Args:
        update (Update): Объект с информацией об обновлении от Telegram.
        context (ContextTypes.DEFAULT_TYPE): Контекст выполнения обработчика.

    '''
    # Создаем сообщение о приостановке
    stop_message = (
        "Бот приостановлен. Используйте /start для возобновления работы."
    )

    # Клавиатура только с /start
    keyboard = [["/start"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard = True, one_time_keyboard = True)

    # Отправляем сообщение с измененной клавиатурой
    await update.message.reply_text(stop_message, reply_markup = reply_markup)

def main() -> None:
    '''
    Основная функция для запуска бота
    '''
    # Получение токена
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    # Проверка, что токен существует
    if not TOKEN:
        logging.error('Токен не найден в переменных окружения. Проверьте файл .env')
        return

    # Создаем приложение бота с указанным токеном
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчик команды /start
    application.add_handler(CommandHandler("start", start))
    # Регистрируем обработчик команды /help
    application.add_handler(CommandHandler("help", help_command))
    # Регистрируем обработчик команды /stop
    application.add_handler(CommandHandler("stop", stop_command))
    # Регистрируем обработчик текстовых сообщений (кроме команд)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Запуск Telegram бота...")
    # Запускаем бота в режиме polling (опроса)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# Точка входа в программу
if __name__ == '__main__':
    main()