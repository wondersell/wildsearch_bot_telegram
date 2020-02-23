import json
import logging

import falcon
from envparse import env
from telegram import Bot, Update

from . import tasks
from .bot import reset_webhook, start_bot

logger = logging.getLogger(__name__)


class CallbackWbCategoryExportResource(object):
    def on_post(self, req, resp):
        if req.has_param('chat_id'):
            bot.send_message(
                chat_id=req.get_param('chat_id'),
                text='🤘 Выгрузка данных по категории готова.\n🧠 Приступаю к анализу. Минутку...',
            )

            tasks.calculate_wb_category_stats.apply_async(
                (),
                {
                    'job_id': req.get_param('job_id'),
                    'chat_id': req.get_param('chat_id'),
                },
                countdown=30,
            )

            resp.status = falcon.HTTP_200
            resp.body = json.dumps({'status': 'ok'})
        else:
            resp.status = falcon.HTTP_500
            resp.body = json.dumps({'error': 'wrong_chat_id'})


class CallbackCategoryListResource(object):
    def on_post(self, req, resp):
        tasks.calculate_wb_category_diff.apply_async(countdown=600)

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

app.add_route('/callback/wb_category_export', CallbackWbCategoryExportResource())
app.add_route('/callback/category_list', CallbackCategoryListResource())
app.add_route('/' + env('TELEGRAM_API_TOKEN'), CallbackTelegramWebhook())
app.add_route('/', CallbackIndex())
