import falcon
import logging
import json

from .scrapinghub_helper import *
from telegram import Bot
from envparse import env


# загружаем конфиг
env.read_envfile()

# Enable logging
logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def get_cat_update_users():
    return env('WILDSEARCH_TEST_USER_LIST').split(',')


class CallbackResource(object):
    def on_post(self, req, resp, type):
        if type == 'category_export':
            if req.has_param('chat_id'):
                bot.send_message(chat_id=req.get_param('chat_id'), text='Выгрузка данных по категории готова')

        if type == 'category_list':
            diff_data = get_categories_diff()

            for uid in get_cat_update_users():
                if diff_data['new_count'] != 0:
                    bot.send_message(chat_id=uid, text=f"Обновились данные по категориям на Wildberries. C последнего "
                                                       f"обновления добавилось {diff_data['new_count']} категорий, "
                                                       f"из них {diff_data['new_unique_count']} уникальных")

                    # перед каждой отправкой нужно перемотать файл в начало
                    diff_data['new_unique_xlsx'].seek(0)

                    bot.send_document(chat_id=uid, document=diff_data['new_unique_xlsx'])
                else:
                    bot.send_message(chat_id=uid, text=f"За последние сутки категории на Wildberries не обновились")

        resp.status = falcon.HTTP_200
        resp.body = json.dumps({'status': 'ok'})


bot = Bot(env('TELEGRAM_API_TOKEN'))

app = falcon.API()
app.req_options.auto_parse_form_urlencoded = True
callback = CallbackResource()
app.add_route('/callback/{type}', callback)
