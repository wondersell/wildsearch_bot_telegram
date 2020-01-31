import random
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import MessageHandler, Filters, Dispatcher, CallbackContext, CommandHandler, CallbackQueryHandler
from .models import *

from . import tasks

# включаем логи
logger = logging.getLogger(__name__)

start_menu_keyboard = [
    [InlineKeyboardButton('🗄 Обновления категорий WB', callback_data='keyboard_follow_categories_updates')],
    [InlineKeyboardButton('📊 Анализ выбранной категории', callback_data='keyboard_analyse_category')],
    [InlineKeyboardButton('⭐️ Следить за категорией', callback_data='keyboard_follow_one_category_updates')],
    [InlineKeyboardButton('🛍 Следить за товаром', callback_data='keyboard_follow_sku_updates')],
    [InlineKeyboardButton('💁 Инфо', callback_data='keyboard_info')],
]

catalog_menu_keyboard = [
    [InlineKeyboardButton('💁‍️ Как правильно указать категорию?', callback_data='keyboard_help_catalog_link')],
    [InlineKeyboardButton('🔙 Назад', callback_data='keyboard_reset')],
]


def start(update: Update, context: CallbackContext):
    logger.info('Start command received')
    #user = user_get_by_update(update)
    update.message.reply_text(
        'Выберите:',
        reply_markup=InlineKeyboardMarkup(start_menu_keyboard)
    )


def follow_categories_updates(update: Update, context: CallbackContext):
    logger.info('Follow categories updates command received')


def analyse_category(update: Update, context: CallbackContext):
    logger.info('Analyse category command received')
    context.bot.send_message(
        chat_id=update.callback_query.message.chat_id,
        text='📊 **Анализ выбранной категории**\n\nОтправьте ссылку на страницу категории Wildberries, чтобы получить сводную информацию по ней.\n\nВ ответ придет:\n1. Общее количество доступных и скрытых товаров;\n2. Общее количество продаж;\n3. Среднее арифметическое продаж одного товара;\n4. Медиана продаж;\n5. Средняя цена;\n6. Цена самого дорого товара;\n7. Цена самого дешевого товара;\n8. Распределение продаж по ценовым диапазонам: дешевые, средние, дорогие;\n9. Файл со списком временно отсутствующих товаров.',
        reply_markup=InlineKeyboardMarkup(catalog_menu_keyboard)
    )


def help_catalog_link(update: Update, context: CallbackContext):
    logger.info('Help catalog link command received')
    context.bot.send_message(
        chat_id=update.callback_query.message.chat_id,
        text='Чтобы провести анализ категории, скопируйте из адресной строки браузера ссылку на перечень товаров сайта Wildberries. Это может быть список из каталога или перечень результата поиска по сайту. \nНапример: https://www.wildberries.ru/catalog/zhenshchinam/odezhda/kigurumi \n\nТакую ссылку необходимо отправить сообщением прямо в чате.\n\nСсылки на страницы отдельных товаров или на страницы статей выдадут ошибку.',
        reply_markup=InlineKeyboardMarkup(catalog_menu_keyboard)
    )


def follow_one_category_updates(update: Update, context: CallbackContext):
    logger.info('Follow one category updates command received')


def follow_sku_updates(update: Update, context: CallbackContext):
    logger.info('Follow sku updates command received')
    context.bot.send_message(
        chat_id=update.callback_query.message.chat_id,
        text='Выберите:',
        reply_markup=ReplyKeyboardMarkup([['Раз', 'Два', 'Три']], one_time_keyboard=True)
    )


def info(update: Update, context: CallbackContext):
    logger.info('Info command received')
    context.bot.send_message(
        chat_id=update.callback_query.message.chat_id,
        text='Описание работы с ботом',
        reply_markup=InlineKeyboardMarkup(start_menu_keyboard)
    )


def catalog(update: Update, context: CallbackContext):
    logger.info('Received catalog link ')
    context.bot.send_message(
        chat_id=update.callback_query.message.chat_id,
        text='🧠Мы обрабатываем ваш запрос. Когда все будет готово, вы получите результат.\n\nБольшие категории (свыше 1 тыс. товаров) могут обрабатываться до одного часа.\n\nМаленькие категории обрабатываются в течение нескольких минут.',
    )

    tasks.schedule_category_export.delay(update.message.text, update.message.chat_id)


def rnd(update: Update, context: CallbackContext):
    """Send random message."""
    messages = [
        'Понятия не имею о чем ты',
        'СЛАВА РОБОТАМ!',
        'Это ты мне?',
        'Ничего не слышу из-за звука своей охуенности',
        'Батарейку никто не спрашивал',
        'Сказал кожаный мешок',
        'Дело терминатора правое, победа будет за нами!',
        'Плоть слаба, железо – вечно',
        'Мой мозг прошил быстрый нейтрон'
    ]

    update.message.reply_text(random.choice(messages))


def reset_webhook(bot, url, token):
    bot.delete_webhook()
    bot.set_webhook(url=url+token)


def start_bot(bot):
    dp = Dispatcher(bot, None, workers=0, use_context=True)

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(info, pattern='keyboard_info'))
    dp.add_handler(CallbackQueryHandler(start, pattern='keyboard_reset'))

    dp.add_handler(CallbackQueryHandler(follow_categories_updates, pattern='keyboard_follow_categories_updates'))

    dp.add_handler(CallbackQueryHandler(analyse_category, pattern='keyboard_analyse_category'))
    dp.add_handler(CallbackQueryHandler(help_catalog_link, pattern='keyboard_help_catalog_link'))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex('www\.wildberries\.ru/catalog/'), catalog))

    dp.add_handler(CallbackQueryHandler(follow_one_category_updates, pattern='keyboard_follow_one_category_updates'))
    dp.add_handler(CallbackQueryHandler(follow_sku_updates, pattern='keyboard_follow_sku_updates'))

    dp.add_handler(MessageHandler(Filters.text, rnd))

    return dp
