from django.urls import path
from .views import career_recom, save_career, gap_analyzer, reset_saved_careers

app_name = "career_analysis"

urlpatterns = [
    path('', career_recom, name='career_recom'),
    path("save-career/", save_career, name="save_career"),
    path("reset-saved-careers/",reset_saved_careers, name="reset_saved_careers"),
    path('gap-analyzer/', gap_analyzer, name='gap_analyzer'),

]
