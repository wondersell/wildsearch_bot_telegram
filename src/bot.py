import logging
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, Dispatcher, Filters, MessageHandler

from . import tasks
from .models import log_command, user_get_by_update

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
    user = user_get_by_update(update)
    log_command(user, 'start')

    update.message.reply_text(
        f'Привет, {user.user_name}! Вот возможные команды:',
        reply_markup=InlineKeyboardMarkup(start_menu_keyboard)
    )


def analyse_category(update: Update, context: CallbackContext):
    logger.info('Analyse category command received')
    user = user_get_by_update(update)
    log_command(user, 'analyse_category')

    context.bot.send_message(
        chat_id=update.callback_query.message.chat_id,
        text='📊 **Анализ выбранной категории**\n\nОтправьте ссылку на страницу категории Wildberries, чтобы получить сводную информацию по ней.\n\nВ ответ придет:\n1. Общее количество доступных и скрытых товаров;\n2. Общее количество продаж;\n3. Среднее арифметическое продаж одного товара;\n4. Медиана продаж;\n5. Средняя цена;\n6. Цена самого дорого товара;\n7. Цена самого дешевого товара;\n8. Распределение продаж по ценовым диапазонам: дешевые, средние, дорогие;\n9. Файл со списком временно отсутствующих товаров.',
        reply_markup=InlineKeyboardMarkup(catalog_menu_keyboard)
    )


def help_catalog_link(update: Update, context: CallbackContext):
    logger.info('Help catalog link command received')
    user = user_get_by_update(update)
    log_command(user, 'help_catalog_link')

    context.bot.send_message(
        chat_id=update.callback_query.message.chat_id,
        text='Чтобы провести анализ категории, скопируйте из адресной строки браузера ссылку на перечень товаров сайта Wildberries. Это может быть список из каталога или перечень результата поиска по сайту. \nНапример: https://www.wildberries.ru/catalog/zhenshchinam/odezhda/kigurumi \n\nТакую ссылку необходимо отправить сообщением прямо в чате.\n\nСсылки на страницы отдельных товаров или на страницы статей выдадут ошибку.',
        reply_markup=InlineKeyboardMarkup(catalog_menu_keyboard)
    )


def info(update: Update, context: CallbackContext):
    logger.info('Info command received')
    user = user_get_by_update(update)
    log_command(user, 'info')
    context.bot.send_message(
        chat_id=update.callback_query.message.chat_id,
        text='Описание работы с ботом',
        reply_markup=InlineKeyboardMarkup(start_menu_keyboard)
    )


def wb_catalog(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    log_command(user, 'wb_catalog', update.message.text)

    if user.can_send_more_catalog_requests():
        tasks.schedule_wb_category_export.delay(update.message.text, update.message.chat_id)
    else:
        update.message.reply_text(f'Сорян, у тебя закончился лимит выгрузок на сегодня')


def rnd(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    log_command(user, 'rnd', update.message.text)

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
        'Мой мозг прошил быстрый нейтрон',
    ]

    update.message.reply_text(random.choice(messages))


def reset_webhook(bot, url, token):
    bot.delete_webhook()
    bot.set_webhook(url=url + token)


def start_bot(bot):
    dp = Dispatcher(bot, None, workers=0, use_context=True)

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(info, pattern='keyboard_info'))
    dp.add_handler(CallbackQueryHandler(start, pattern='keyboard_reset'))

    dp.add_handler(CallbackQueryHandler(analyse_category, pattern='keyboard_analyse_category'))
    dp.add_handler(CallbackQueryHandler(help_catalog_link, pattern='keyboard_help_catalog_link'))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex('www\.wildberries\.ru/catalog/'), wb_catalog))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex('www\.wildberries\.ru/brands/'), wb_catalog))

    dp.add_handler(MessageHandler(Filters.text, rnd))

    return dp
