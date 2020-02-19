import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, Dispatcher, Filters, MessageHandler

from . import tasks
from .models import log_command, user_get_by_update

# включаем логи
logger = logging.getLogger(__name__)

catalog_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton('💁‍️ Как правильно указать категорию?', callback_data='keyboard_help_catalog_link')],
])

no_limits_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton('👨‍🚀 Чат с поддержкой', url='http://wondersell.ru')],
])

reply_keyboard = ReplyKeyboardMarkup([['ℹ️ О сервисе', '🚀 Увеличить лимит запросов']], resize_keyboard=True)


def start(update: Update, context: CallbackContext):
    logger.info('Start command received')
    user = user_get_by_update(update)
    log_command(user, 'start')

    context.bot.send_message(
        chat_id=user.chat_id,
        text=f'Приветствую, {user.full_name}!',
        reply_markup=reply_keyboard,
    )

    context.bot.send_message(
        chat_id=user.chat_id,
        text=f'📊 Этот телеграм бот поможет собирать данные о товарах на Wildberries и анализировать их.\n\n📲 Отправьте ссылку на интересующую категорию Wildberries, чтобы получить сводную информацию по ней.\n\n📑 Также вы получите Эксель файл с полной выгрузкой данных для самостоятельного и детального анализа.\n\n🔔  Вам доступно {user.catalog_requests_left_count()} из {user.daily_catalog_requests_limit} запросов. Ограничение обнулится через 24 часа с момента последнего анализа.',
        reply_markup=catalog_menu_keyboard,
    )


def analyse_category(update: Update, context: CallbackContext):
    logger.info('Analyse category command received')
    user = user_get_by_update(update)
    log_command(user, 'analyse_category')

    context.bot.send_message(
        chat_id=user.chat_id,
        text='📊 Анализ выбранной категории\n\nОтправьте ссылку на страницу категории Wildberries, чтобы получить сводную информацию по ней.\n\nВ ответ придет:\n1. Общее количество доступных и скрытых товаров;\n2. Общее количество продаж;\n3. Среднее арифметическое продаж одного товара;\n4. Медиана продаж;\n5. Средняя цена;\n6. Цена самого дорого товара;\n7. Цена самого дешевого товара;\n8. Распределение продаж по ценовым диапазонам: дешевые, средние, дорогие;\n9. Файл со списком временно отсутствующих товаров.',
        reply_markup=catalog_menu_keyboard,
        disable_web_page_preview=True,
    )


def help_catalog_link(update: Update, context: CallbackContext):
    logger.info('Help catalog link command received')
    user = user_get_by_update(update)
    log_command(user, 'help_catalog_link')

    context.bot.send_message(
        chat_id=user.chat_id,
        text='☝️ Чтобы провести анализ категории, скопируйте из адресной строки браузера ссылку на перечень товаров сайта Wildberries. Это может быть список из каталога или перечень результата поиска по сайту. \nНапример: https://www.wildberries.ru/catalog/zhenshchinam/odezhda/kigurumi \n\n💬 Такую ссылку необходимо отправить сообщением прямо в чате.\n\n⚠️ Ссылки на страницы отдельных товаров или на страницы статей выдадут ошибку.',
        disable_web_page_preview=True,
    )


def info(update: Update, context: CallbackContext):
    logger.info('Info command received')
    user = user_get_by_update(update)
    log_command(user, 'info')

    context.bot.send_message(
        chat_id=user.chat_id,
        text='📊 Этот телеграм бот поможет собирать данные о товарах на Wildberries и анализировать их.\n\n📲 Отправьте ссылку на интересующую категорию Wildberries, чтобы получить сводную информацию по ней.\n\n📑 Также вы получите Эксель файл с полной выгрузкой данных для самостоятельного и детального анализа.',
        reply_markup=no_limits_menu_keyboard,
    )


def no_limits(update: Update, context: CallbackContext):
    logger.info('Info command received')
    user = user_get_by_update(update)
    log_command(user, 'no_limits')

    context.bot.send_message(
        chat_id=user.chat_id,
        text=f'Если вы хотите увеличить или снять лимит запросов напишите нам в чат поддержки запрос с фразой «Снимите лимит запросов».',
        reply_markup=no_limits_menu_keyboard,
    )


def wb_catalog(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    log_command(user, 'wb_catalog', update.message.text)

    if user.can_send_more_catalog_requests():
        tasks.schedule_wb_category_export.delay(update.message.text, update.message.chat_id)
    else:
        dt = user.next_free_catalog_request_time()

        context.bot.send_message(
            chat_id=user.chat_id,
            text=f'💫 Ваш лимит запросов закончился. Чтобы продолжить работу, напишите нам в чат поддержки с запросом на снятие ограничения, либо дождитесь восстановления лимита. Новый запрос вам станет доступным {dt.day} {dt.month} в {dt.hour} часов {dt.minute} минут',
        )


def rnd(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    log_command(user, 'rnd', update.message.text)

    context.bot.send_message(
        chat_id=user.chat_id,
        text='⚠️🤷 Непонятная команда.\nСкорее всего, вы указали неправильную команду. Сейчас бот может анализировать только ссылки на каталоги Wildberries.',
        reply_markup=catalog_menu_keyboard,
    )


def reset_webhook(bot, url, token):
    bot.delete_webhook()
    bot.set_webhook(url=url + token)


def start_bot(bot):
    dp = Dispatcher(bot, None, workers=0, use_context=True)

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex('ℹ️ О сервисе'), info))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex('🚀 Увеличить лимит запросов'), no_limits))

    dp.add_handler(CallbackQueryHandler(analyse_category, pattern='keyboard_analyse_category'))
    dp.add_handler(CallbackQueryHandler(help_catalog_link, pattern='keyboard_help_catalog_link'))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'www\.wildberries\.ru/catalog/'), wb_catalog))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'www\.wildberries\.ru/brands/'), wb_catalog))

    dp.add_handler(MessageHandler(Filters.all, rnd))

    return dp
