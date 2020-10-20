import logging

import click
from envparse import env
from telegram import Bot

logger = logging.getLogger(__name__)

bot = Bot(env('TELEGRAM_API_TOKEN'))


@click.command()
@click.argument('text')
@click.option(
    '--chat-ids', '-i',
    help='chat IDs for bulk sending',
)
def main(text, chat_ids):
    chat_ids = str.split(chat_ids, ',')

    for chat_id in chat_ids:
        try:
            bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown', disable_web_page_preview=True)

            print(f'Sending message to chat {chat_id} success')
        except Exception as error:
            print(f'Sending message to chat {chat_id} failed: {str(error)}')


if __name__ == '__main__':
    main()
