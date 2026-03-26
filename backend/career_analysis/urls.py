from django.urls import path
from .views import (
    career_recom, save_career, gap_analyzer, reset_saved_careers,
    toggle_week_progress, roadmap_page, add_completed_skill,
    profile_page, update_profile, generate_resume, job_analyzer,
    get_skill_roadmap, generate_topic_quiz, generate_topic_notes, get_topic_courses, submit_review, chat_with_mentor,
    community_view, create_community_post, toggle_like_post, add_post_comment, delete_post_comment, chat_view, send_direct_message, get_chat_notifications, get_messages
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
    path("generate-topic-quiz/", generate_topic_quiz, name="generate_topic_quiz"),
    path("generate-topic-notes/", generate_topic_notes, name="generate_topic_notes"),
    path("get-topic-courses/", get_topic_courses, name="get_topic_courses"),
    path("submit-review/", submit_review, name="submit_review"),
    path("chat-with-mentor/", chat_with_mentor, name="chat_with_mentor"),

    # Community & Chat
    path("community/", community_view, name="community"),
    path("create-post/", create_community_post, name="create_post"),
    path("like-post/", toggle_like_post, name="like_post"),
    path("chat/", chat_view, name="chat"),
    path("get-messages/", get_messages, name="get_messages"),
    path("send-message/", send_direct_message, name="send_message"),
    path("add-comment/", add_post_comment, name="add_comment"),
    path("delete-comment/", delete_post_comment, name="delete_comment"),
    path("notifications/", get_chat_notifications, name="chat_notifications"),
]
