import logging

import json_log_formatter
import sentry_sdk
from envparse import env
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.falcon import FalconIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# загружаем конфиг
env.read_envfile()

# включаем логи
logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s',
                    level=logging.INFO)

# formatter = json_log_formatter.JSONFormatter()

# json_handler = logging.FileHandler(filename='/var/log/wildsearch_app_log.json')
# json_handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
# logger.addHandler(json_handler)


# включаем Sentry
if env('SENTRY_DSN', default=None) is not None:
    sentry_sdk.init(env('SENTRY_DSN'), integrations=[FalconIntegration(), CeleryIntegration(), RedisIntegration()])
