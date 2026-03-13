from mongoengine import Document, StringField, EmailField, ListField, DictField, DateTimeField, IntField, URLField
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


class UserProfile(Document):
    user_email = EmailField(required=True, unique=True)
    full_name = StringField(default="")
    phone = StringField(default="")
    current_occupation = StringField(default="")
    target_role = StringField(default="")
    education = StringField(default="")
    specialization = StringField(default="")
    current_skills = StringField(default="")  # comma-separated
    profile_pic = StringField(default=None)
    bio = StringField(default="")
    linkedin_url = URLField(default=None)
    github_url = URLField(default=None)
    location = StringField(default="")

    education_list = ListField(DictField(), default=[])  # List of {degree, institution, year, cgpa}
    projects = ListField(DictField(), default=[])       # List of {title, tech, description}
    certifications = ListField(StringField(), default=[])
    achievements = ListField(StringField(), default=[])
    hobbies = ListField(StringField(), default=[])

    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "user_profiles",
        "indexes": ["user_email"]
    }


class CompletedRoadmapSkill(Document):
    """Tracks skills completed by user through roadmap checkboxes"""
    user_email = EmailField(required=True)
    skill_name = StringField(required=True)
    skill_type = StringField(default="Technical Skill")
    completed_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "completed_roadmap_skills",
        "indexes": ["user_email"]
    }


class CachedRoadmap(Document):
    """Caches AI-generated roadmaps to avoid repeated API calls"""
    user_email = EmailField(required=True)
    skill_name = StringField(required=True)
    skill_type = StringField(default="Technical Skill")
    roadmap_data = DictField()  # stores the full roadmap JSON
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "cached_roadmaps",
        "indexes": [
            {"fields": ["user_email", "skill_name"], "unique": True}
        ]
    }


class PasswordResetToken(Document):
    """Stores password reset tokens for custom MongoEngine-based auth"""
    email = EmailField(required=True)
    token = StringField(required=True, unique=True)
    created_at = DateTimeField(default=datetime.utcnow)
    used = IntField(default=0)  # 0 = unused, 1 = used

    meta = {
        "collection": "password_reset_tokens",
        "indexes": ["email", "token"]
    }