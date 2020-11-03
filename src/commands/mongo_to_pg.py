import logging

import click
from envparse import env
from telegram import Bot

from ..models import LogCommandItem as MongoLogCommandItem
from ..models import User as MongoUser
from ..models_peewee import LogCommandItem as PgLogCommandItem
from ..models_peewee import User as PgUser
from ..models_peewee import create_tables

logger = logging.getLogger(__name__)

bot = Bot(env('TELEGRAM_API_TOKEN'))


@click.command()
def main():
    create_tables()

    for user in MongoUser.objects():
        print(f'Saving user #{user.chat_id}')  # noqa: T001

        PgUser.create(
            chat_id=user.chat_id,
            user_name=user.user_name,
            full_name=user.full_name,
            daily_catalog_requests_limit=user.daily_catalog_requests_limit,
            catalog_requests_blocked=user.catalog_requests_blocked,
            subscribe_to_wb_categories_updates=user.subscribe_to_wb_categories_updates,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    for command in MongoLogCommandItem.objects():
        print('Saving command log for unknown')  # noqa: T001

        PgLogCommandItem.create(
            user=command.user.chat_id,
            command=command.command,
            message=command.message,
            status=command.status,
            created_at=command.created_at,
        )


if __name__ == '__main__':
    main()
