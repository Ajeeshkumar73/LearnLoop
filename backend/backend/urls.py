from django.urls import path, include

urlpatterns = [
    path('', include('main.urls')),
    path('auth/', include('accounts.urls')),
    path('career/', include('career_analysis.urls')),
]
