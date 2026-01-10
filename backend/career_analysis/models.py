from mongoengine import Document, StringField, EmailField, ListField, DictField, DateTimeField
from datetime import datetime

class CareerSubmission(Document):
    # link submission to the user by email
    user_email = EmailField(required=True)  

    # user inputs
    education = StringField()
    specialization = StringField()
    expert_skills = StringField()
    intermediate_skills = StringField()
    soft_skills = ListField(StringField())
    interests = StringField()
    personality = ListField(StringField())

    # AI results
    results = ListField(DictField())  # store AI recommendations
    avg_match = StringField()          # optional summary score

    # timestamp
    created_at = DateTimeField(default=datetime.utcnow)

class SavedCareer(Document):
    # link to logged-in user
    user_email = EmailField(required=True)

    # saved career info
    career_name = StringField(required=True)
            

    # timestamp
    saved_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "saved_careers",
        "indexes": [
            {"fields": ["user_email", "career_name"], "unique": True}
        ]
    }