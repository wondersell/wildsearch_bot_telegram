from unittest.mock import patch

from src import tasks


@patch('telegram.Bot.send_document')
@patch('telegram.Bot.send_message')
def test_send_wb_category_update_message_text_only(patched_send_message, patched_send_document):
    uid = 12345
    message = 'um hi?'

    tasks.send_wb_category_update_message(uid, message)

    patched_send_message.assert_called_with(chat_id=12345, text='um hi?')
    patched_send_document.assert_not_called()