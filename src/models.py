from datetime import datetime, timedelta

from envparse import env
from mongoengine import BooleanField, DateTimeField, Document, IntField, ReferenceField, StringField, connect
from telegram import Update

env.read_envfile()

connect(host=env('MONGODB_URI'))


def user_get_by(*args, **kwargs):
    return User.objects(*args, **kwargs).first()


def user_get_by_update(update: Update):
    if update.message:
        message = update.message
    else:
        message = update.callback_query.message

    matched = User.objects(chat_id=message.chat.id)

    if matched.count():
        return matched.first()

    full_name = ''
    if message.from_user.first_name:
        full_name += message.from_user.first_name
    if message.from_user.last_name:
        full_name += ' ' + message.from_user.last_name

    return User(
        chat_id=message.chat_id,
        user_name=message.from_user.username,
        full_name=full_name,
    ).save()


def log_command(user, command: str, message: str = ''):
    return LogCommandItem(
        user=user,
        command=command,
        message=message,
    ).save()


def get_subscribed_to_wb_categories_updates() -> []:
    return User.objects(subscribe_to_wb_categories_updates=True)


class User(Document):
    chat_id = IntField(required=True, primary_key=True)
    user_name = StringField()
    full_name = StringField()
    daily_catalog_requests_limit = IntField(default=int(env('SETTINGS_FREE_DAILY_REQUESTS', 5)))
    catalog_requests_blocked = BooleanField(default=False)
    subscribe_to_wb_categories_updates = BooleanField(default=False)
    created_at = DateTimeField()
    updated_at = DateTimeField()

    def can_send_more_catalog_requests(self) -> bool:
        """Throttling here."""
        if self.catalog_requests_blocked is True:
            return False

        if self.today_catalog_requests_count() >= self.daily_catalog_requests_limit:
            return False

        return True

    def today_catalog_requests_count(self) -> int:
        """Get catalog requests count based on requests log."""
        time_from = datetime.now() - timedelta(hours=24)

        return LogCommandItem.objects(
            user=self.id,
            command='wb_catalog',
            status='success',
            created_at__gte=time_from).count()

    def catalog_requests_left_count(self) -> int:
        return self.daily_catalog_requests_limit - self.today_catalog_requests_count()

    def next_free_catalog_request_time(self) -> datetime:
        if self.today_catalog_requests_count() < self.daily_catalog_requests_limit:
            return datetime.now()

        oldest_request = LogCommandItem.objects(
            user=self.id,
            command='wb_catalog',
        ).order_by('+created_at').limit(self.daily_catalog_requests_limit).first()

        return oldest_request['created_at'] + timedelta(hours=24)

    def save(self, *args, **kwargs):
        """Add timestamps for creating and updating items."""
        if not self.created_at:
            self.created_at = datetime.now()

        self.updated_at = datetime.now()

        return super(User, self).save(*args, **kwargs)


class LogCommandItem(Document):
    user = ReferenceField(User)
    command = StringField()
    message = StringField()
    status = StringField()
    created_at = DateTimeField()

    def set_status(self, status):
        self.status = status
        self.save()
        return self

    def save(self, *args, **kwargs):
        """Add timestamps for creating and updating items."""
        if not self.created_at:
            self.created_at = datetime.now()

        return super(LogCommandItem, self).save(*args, **kwargs)
