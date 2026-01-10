from mongoengine import Document, StringField, EmailField
from werkzeug.security import generate_password_hash, check_password_hash


class User(Document):
    email = EmailField(required=True, unique=True)
    password = StringField(required=True)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)


class Profile(Document):
    user = StringField(required=True)  # store user email
    full_name = StringField(required=True)
