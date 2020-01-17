import json

import falcon
from sentry_sdk.integrations.falcon import FalconIntegration
from telegram import Bot, Update
from envparse import env

from . import tasks
from .scrapinghub_helper import *
from .bot import reset_webhook, start_bot

# загружаем конфиг
env.read_envfile()

# включаем логи
logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# включаем Sentry
if env('SENTRY_DSN', default=None) is not None:
    sentry_sdk.init(env('SENTRY_DSN'), integrations=[FalconIntegration()])


class CallbackCategoryExportResource(object):
    def on_post(self, req, resp):
        if req.has_param('chat_id'):
            bot.send_message(chat_id=req.get_param('chat_id'), text='Выгрузка данных по категории готова')

            resp.status = falcon.HTTP_200
            resp.body = json.dumps({'status': 'ok'})
        else:
            resp.status = falcon.HTTP_500
            resp.body = json.dumps({'error': 'wrong_chat_id'})


class CallbackCategoryListResource(object):
    def on_post(self, req, resp):
        tasks.calculate_wb_category_diff.delay(countdown=600)

        resp.status = falcon.HTTP_200
        resp.body = json.dumps({'status': 'ok'})


class CallbackTelegramWebhook(object):
    def on_post(self, req, resp):
        bot_dispatcher.process_update(Update.de_json(json.load(req.bounded_stream), bot))

        resp.status = falcon.HTTP_200
        resp.body = json.dumps({'status': 'ok'})


class CallbackIndex(object):
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.body = json.dumps({'status': 'lucky_you'})


bot = Bot(env('TELEGRAM_API_TOKEN'))
reset_webhook(bot, env('WILDSEARCH_WEBHOOKS_DOMAIN'), env('TELEGRAM_API_TOKEN'))
bot_dispatcher = start_bot(bot)

app = falcon.API()
app.req_options.auto_parse_form_urlencoded = True

app.add_route('/callback/category_export', CallbackCategoryExportResource())
app.add_route('/callback/category_list', CallbackCategoryListResource())
app.add_route('/' + env('TELEGRAM_API_TOKEN'), CallbackTelegramWebhook())
app.add_route('/', CallbackIndex())
