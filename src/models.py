from datetime import datetime
from telegram import Update
from mongoengine import connect
from mongoengine import Document
from mongoengine import BooleanField, IntField, StringField, DateTimeField, ReferenceField
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


def log_command(user, command: str, message: str):
    return LogCommandItem(
        user=user,
        command=command,
        message=message
    ).save()


class User(Document):
    chat_id = IntField(required=True, primary_key=True)
    user_name = StringField()
    full_name = StringField()
    daily_catalog_requests_limit = IntField(default=5)
    catalog_requests_blocked = BooleanField(default=False)
    created_at = DateTimeField()
    updated_at = DateTimeField()

    def can_send_more_catalog_requests(self) -> bool:
        """Throttling here"""
        if self.catalog_requests_blocked is True:
            return False

        if self.today_catalog_requests_count() >= self.daily_catalog_requests_limit:
            return False

        return True

    def today_catalog_requests_count(self):
        """Get catalog requests count based on requests log"""
        midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        return LogCommandItem.objects(
            user=self.id,
            command='wb_catalog',
            created_at__gte=midnight).count()

    def save(self, *args, **kwargs):
        """Add timestamps for creating and updating items"""
        if not self.created_at:
            self.created_at = datetime.now()

        self.updated_at = datetime.now()

        return super(User, self).save(*args, **kwargs)


class LogCommandItem(Document):
    user = ReferenceField(User)
    command = StringField()
    message = StringField()
    created_at = DateTimeField()

    def save(self, *args, **kwargs):
        """Add timestamps for creating and updating items"""
        if not self.created_at:
            self.created_at = datetime.now()

        return super(LogCommandItem, self).save(*args, **kwargs)
