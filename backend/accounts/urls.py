from django.urls import path
from .views import register, login_view, logout_view, forgot_password, reset_password, google_signin

app_name = "accounts" 

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    path("logout/", logout_view, name="logout"),
    path("forgot-password/", forgot_password, name="forgot_password"),
    path("reset-password/<str:token>/", reset_password, name="reset_password"),
    path("google-signin/", google_signin, name="google_signin"),
]
