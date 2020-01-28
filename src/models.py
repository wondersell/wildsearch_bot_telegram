import datetime

from telegram import Update
from mongoengine import *
from envparse import env


env.read_envfile()

connect(host=env('MONGODB_URI'))


def user_get_by(*args, **kwargs):
    return User.objects(*args, **kwargs).first()


def user_get_by_update(update: Update):
    matched = User.objects(chat_id=update.message.chat_id)

    if matched.count():
        return matched.first()

    return User(
        chat_id=update.message.chat_id,
        user_name=update.message.from_user.username,
        full_name=update.message.from_user.first_name + ' ' + update.message.from_user.last_name
    ).save()


class User(Document):
    chat_id = IntField()
    user_name = StringField()
    full_name = StringField()
    created_at = DateTimeField()
    updated_at = DateTimeField()

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.datetime.now()

        self.updated_at = datetime.datetime.now()

        return super(User, self).save(*args, **kwargs)
