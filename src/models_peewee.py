from datetime import datetime, timedelta

import peewee as pw
from envparse import env
from playhouse.db_url import connect
from telegram import Update

env.read_envfile()
db = connect(env('DATABASE_URL', cast=str, default='sqlite:///db.sqlite'))


class User(pw.Model):
    chat_id = pw.IntegerField(primary_key=True)
    user_name = pw.CharField(index=True, null=True)
    full_name = pw.CharField(index=True, null=True)
    daily_catalog_requests_limit = pw.IntegerField(default=int(env('SETTINGS_FREE_DAILY_REQUESTS', 5)))
    catalog_requests_blocked = pw.BooleanField(default=False, index=True)
    subscribe_to_wb_categories_updates = pw.BooleanField(default=False, index=True)
    created_at = pw.DateTimeField(index=True)
    updated_at = pw.DateTimeField(index=True)

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

        return LogCommandItem.select().where(
            LogCommandItem.user == self.chat_id,
            LogCommandItem.command == 'wb_catalog',
            LogCommandItem.status == 'success',
            LogCommandItem.created_at >= time_from).count()

    def catalog_requests_left_count(self) -> int:
        return self.daily_catalog_requests_limit - self.today_catalog_requests_count()

    def next_free_catalog_request_time(self) -> datetime:
        if self.today_catalog_requests_count() < self.daily_catalog_requests_limit:
            return datetime.now()

        oldest_request = LogCommandItem.select().where(
            LogCommandItem.user == self.chat_id,
            LogCommandItem.command == 'wb_catalog',
        ).order_by(LogCommandItem.created_at).limit(self.daily_catalog_requests_limit).first()

        return oldest_request.created_at + timedelta(hours=24)

    def save(self, *args, **kwargs):
        """Add timestamps for creating and updating items."""
        if not self.created_at:
            self.created_at = datetime.now()

        self.updated_at = datetime.now()

        return super(User, self).save(*args, **kwargs)

    class Meta:
        database = db


class LogCommandItem(pw.Model):
    user = pw.ForeignKeyField(User, index=True)
    command = pw.CharField(index=True, null=True)
    message = pw.CharField(null=True)
    status = pw.CharField(null=True)
    created_at = pw.DateTimeField(index=True)

    def set_status(self, status):
        self.status = status
        self.save()
        return self

    def save(self, *args, **kwargs):
        """Add timestamps for creating and updating items."""
        if not self.created_at:
            self.created_at = datetime.now()

        return super(LogCommandItem, self).save(*args, **kwargs)

    class Meta:
        database = db


def user_get_by_chat_id(chat_id):
    return User.get(User.chat_id == chat_id)


def user_get_by_update(update: Update):
    if update.message:
        message = update.message
    else:
        message = update.callback_query.message

    full_name = ''
    if message.chat.first_name:
        full_name += message.chat.first_name
    if message.from_user.last_name:
        full_name += ' ' + message.chat.last_name

    instance, created = User.get_or_create(
        chat_id=message.chat.id,
        defaults={
            'chat_id': message.chat.id,
            'user_name': message.chat.username,
            'full_name': full_name,
        },
    )

    return instance


def log_command(user, command: str, message: str = ''):
    command = LogCommandItem(
        user=user,
        command=command,
        message=message,
    )

    command.save()

    return command


def get_subscribed_to_wb_categories_updates() -> []:
    return User.select().where(User.subscribe_to_wb_categories_updates == True)  # noqa: E712


def create_tables():
    db.create_tables([User, LogCommandItem])
