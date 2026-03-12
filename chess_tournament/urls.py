from django.contrib import admin
from django.urls import path, include
from accounts.views import api_login_view, api_register_view

from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/login', api_login_view, name='api_login'),
    path('api/register', api_register_view, name='api_register'),
    path('accounts/', include('accounts.urls')),
    path('tournament/', include('tournaments.urls')),
    path('match/', include('matches.urls')),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
]

