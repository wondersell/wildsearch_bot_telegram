import datetime

from mongoengine import *
from envparse import env


env.read_envfile()

connect(host=env('MONGODB_URI'))


def user_get_or_created(*args, **kwargs):
    matched = User.objects(*args, **kwargs)

    if matched.count():
        return matched.first()
    else:
        return User(*args, **kwargs).save()



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
