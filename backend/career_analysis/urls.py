from django.urls import path
from .views import (
    career_recom, save_career, gap_analyzer, reset_saved_careers,
    toggle_week_progress, roadmap_page, add_completed_skill,
    profile_page, update_profile, generate_resume, job_analyzer,
    get_skill_roadmap
)

app_name = "career_analysis"

urlpatterns = [
    path('', career_recom, name='career_recom'),
    path("save-career/", save_career, name="save_career"),
    path("reset-saved-careers/", reset_saved_careers, name="reset_saved_careers"),
    path('gap-analyzer/', gap_analyzer, name='gap_analyzer'),
    path("toggle-week-progress/", toggle_week_progress, name="toggle_week_progress"),

    # New routes
    path("roadmap/", roadmap_page, name="roadmap_page"),
    path("add-completed-skill/", add_completed_skill, name="add_completed_skill"),
    path("profile/", profile_page, name="profile"),
    path("update-profile/", update_profile, name="update_profile"),
    path("generate-resume/", generate_resume, name="generate_resume"),
    path("job-analyzer/", job_analyzer, name="job_analyzer"),
    path("get-skill-roadmap/", get_skill_roadmap, name="get_skill_roadmap"),
]
