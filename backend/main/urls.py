from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register', views.register_view, name='register'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/delete-user/<str:email>/', views.delete_user, name='delete_user'),
    path('admin-dashboard/delete-post/<str:post_id>/', views.delete_post, name='delete_post'),
    path('admin-dashboard/delete-support/<str:support_id>/', views.delete_support, name='delete_support'),
]
