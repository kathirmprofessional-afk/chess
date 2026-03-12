from django.contrib import admin
from django.urls import path, include
from accounts.views import api_login_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/login', api_login_view, name='api_login'),
    path('accounts/', include('accounts.urls')),
    path('tournament/', include('tournaments.urls')),
    path('match/', include('matches.urls')),
    path('', lambda request: __import__('django.shortcuts', fromlist=['redirect']).redirect('dashboard'), name='home'),
]

