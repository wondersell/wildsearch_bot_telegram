import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, Dispatcher, Filters, MessageHandler

from . import tasks
from .models import log_command, user_get_by_update

# включаем логи
logger = logging.getLogger(__name__)

reply_keyboard = ReplyKeyboardMarkup([['ℹ️ О сервисе', '🚀 Увеличить лимит запросов']], resize_keyboard=True)


def process_event(event, user):
    logger.info(event)
    tasks.track_amplitude.delay(chat_id=user.chat_id, event=event)


def process_command(name, user, text=''):
    slug_list = {
        'Started bot': 'help_start',
        'Sent command "Help analyse category"': 'help_analyse_category',
        'Sent command "Help catalog link"': 'help_catalog_link',
        'Sent command "Info"': 'help_info',
        'Sent command "Feedback"': 'help_feedback',
        'Sent command "No limits"': 'help_no_limits',
        'Sent unknown command': 'help_command_not_found',
        'Sent command "WB catalog"': 'wb_catalog',
        'Sent not supported marketplace command': 'help_marketplace_not_supported',
        'Sent command on maintenance mode': 'help_maintenance_mode',
    }

    log_item = log_command(user, slug_list[name], text)
    process_event(name, user)

    return log_item


def help_start(update: Update, context: CallbackContext):
    user = user_get_by_update(update)

    tasks.add_user_to_crm(user.chat_id)

    process_command(name='Started bot', user=user)

    context.bot.send_message(
        chat_id=user.chat_id,
        text=f'Приветствую, {user.full_name}!\n\n📊 Этот телеграм бот поможет собирать данные о товарах на Wildberries и анализировать их.\n\n📲 Отправьте ссылку на интересующую категорию Wildberries, чтобы получить отчет с полной информацией по ней.\n\n📑 Вам доступно {user.catalog_requests_left_count()} из {user.daily_catalog_requests_limit} запросов. Ограничение обнулится через 24 часа с момента последнего анализа.',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('💁‍️ Как правильно указать категорию?', callback_data='keyboard_help_catalog_link')],
        ]),
    )


def help_analyse_category(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    process_command(name='Sent command "Help analyse category"', user=user)

    context.bot.send_message(
        chat_id=user.chat_id,
        text='📊 Анализ выбранной категории\n\nОтправьте ссылку на страницу категории Wildberries, чтобы получить сводную информацию по ней.\n\nВ ответ придет сводная информация по категории, а так же расширенный PDF отчет. Пример отчета можно посмотреть на сайте бота по адресу https://wondersell.ru/wildsearch',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('💁‍️ Как правильно указать категорию?', callback_data='keyboard_help_catalog_link')],
        ]),
        disable_web_page_preview=True,
    )


def help_catalog_link(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    process_command(name='Sent command "Help catalog link"', user=user)

    context.bot.send_message(
        chat_id=user.chat_id,
        text='👉️ Чтобы провести анализ категории, скопируйте из адресной строки браузера ссылку на перечень товаров сайта Wildberries. Это может быть список из каталога или перечень результата поиска по сайту. \nНапример: https://www.wildberries.ru/catalog/zhenshchinam/odezhda/kigurumi \n\n💬 Такую ссылку необходимо отправить сообщением прямо в чате.\n\n⚠️ Ссылки на страницы отдельных товаров или на страницы статей выдадут ошибку.',
        disable_web_page_preview=True,
    )


def help_info(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    process_command(name='Sent command "Info"', user=user)

    context.bot.send_message(
        chat_id=user.chat_id,
        text='📊 Этот телеграм бот поможет собирать данные о товарах на Wildberries и анализировать их.\n\n📲 Отправьте ссылку на интересующую категорию Wildberries, чтобы получить сводную информацию по ней.\n\n📑 Также вы получите персональый PDF отчет с подробной информацией о категории.\n\n💁‍Если вы не нашли нужный показатель, напишите нам сообщение с его описанием и мы постараемся добавить его в следующих версиях отчета.',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('💁‍️ Как правильно указать категорию?', callback_data='keyboard_help_catalog_link')],
            [InlineKeyboardButton('👨‍🚀 Написать в поддержку', url='https://t.me/wildsearch_support_bot')],
        ]),
    )


def help_feedback(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    process_command(name='Sent command "Feedback"', user=user)

    context.bot.send_message(
        chat_id=user.chat_id,
        text='✉️ Если вам нужна помощь, напишите нам весточку на wildsearch@wondersell.ru',
    )


def help_no_limits(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    process_command(name='Sent command "No limits"', user=user)

    context.bot.send_message(
        chat_id=user.chat_id,
        text='Если вы хотите увеличить или снять лимит запросов напишите нам в чат поддержки запрос с фразой «Снимите лимит запросов».',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('👨‍🚀 Написать в поддержку', url='https://t.me/wildsearch_support_bot')],
        ]),
    )


def help_command_not_found(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    process_command(name='Sent unknown command', user=user, text=update.message.text)

    context.bot.send_message(
        chat_id=user.chat_id,
        text='⚠️🤷 Непонятная команда.\nСкорее всего, вы указали неправильную команду. Сейчас бот может анализировать только ссылки на каталоги Wildberries.',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('💁‍️ Как правильно указать категорию?', callback_data='keyboard_help_catalog_link')],
        ]),
    )


def help_marketplace_not_supported(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    process_command(name='Sent not supported marketplace command', user=user, text=update.message.text)

    context.bot.send_message(
        chat_id=user.chat_id,
        text='⚠️🤷 Сейчас бот может анализировать только ссылки на каталоги Wildberries, другие площадки пока не поддерживаются',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('💁‍️ Как правильно указать категорию?', callback_data='keyboard_help_catalog_link')],
        ]),
    )


def help_maintenance_mode(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    process_command(name='Sent command on maintenance mode', user=user, text=update.message.text)

    context.bot.send_message(
        chat_id=user.chat_id,
        text='🧩 Наш сервис обновляется. Мы обновляем сервис и не можем обработать ваш запрос. Как только обновление будет готово мы сразу же оповестим вас.',
    )


def wb_catalog(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    log_item = process_command(name='Sent command "WB catalog"', user=user, text=update.message.text)

    if user.can_send_more_catalog_requests() is False:
        dt = user.next_free_catalog_request_time()
        context.bot.send_message(
            chat_id=user.chat_id,
            text=f'💫⚠️ Ваш лимит запросов закончился.\nЧтобы продолжить работу, напишите нам в чат поддержки с запросом на снятие ограничения, либо дождитесь восстановления лимита. Это произойдет {dt.day}.{dt.month} в {dt.hour}:{dt.minute}',
        )
        process_event(user=user, event='Received "Out of requests" error')

    else:
        tasks.schedule_category_export.delay(update.message.text, update.message.chat_id, log_item.id)
        process_event(user=user, event='Started WB catalog export')


def reset_webhook(bot, url, token):
    bot.delete_webhook()
    bot.set_webhook(url=url + token)


def start_bot(bot):
    dp = Dispatcher(bot, None, workers=0, use_context=True)

    dp.add_handler(CommandHandler('start', help_start))
    dp.add_handler(CommandHandler('help', help_start))

    dp.add_handler(MessageHandler(Filters.text & Filters.regex('ℹ️ О сервисе'), help_info))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex('🚀 Увеличить лимит запросов'), help_no_limits))

    dp.add_handler(CallbackQueryHandler(help_analyse_category, pattern='keyboard_analyse_category'))
    dp.add_handler(CallbackQueryHandler(help_catalog_link, pattern='keyboard_help_catalog_link'))
    dp.add_handler(CallbackQueryHandler(help_feedback, pattern='keyboard_help_info_feedback'))

    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'(ozon\.ru|beru\.ru|goods\.ru|tmall\.ru|lamoda\.ru)/'), help_marketplace_not_supported))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'www\.wildberries\.ru/catalog/.*/detail\.aspx'), help_command_not_found))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'www\.wildberries\.ru/catalog/'), wb_catalog))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'www\.wildberries\.ru/brands/'), wb_catalog))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'www\.wildberries\.ru/promotions/'), wb_catalog))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'www\.wildberries\.ru/search\?text='), wb_catalog))

    dp.add_handler(MessageHandler(Filters.all, help_command_not_found))

    return dp
