from mongoengine import Document, StringField, EmailField, ListField, DictField, DateTimeField, IntField
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
    user_email = StringField(required=True)
    career_name = StringField(required=True)
    career_icon = StringField(default="work")

    avg_match = IntField()
    results = ListField(DictField())

    created_at = DateTimeField(default=datetime.utcnow)


    meta = {
        "collection": "saved_careers",
        "indexes": [
            {"fields": ["user_email", "career_name"], "unique": True}
        ]
    }


class SkillProgress(Document):
    user_email = StringField(required=True)
    skill_name = StringField(required=True)
    completed_weeks = ListField(IntField())    