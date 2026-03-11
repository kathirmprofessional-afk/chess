from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('tournament/', include('tournaments.urls')),
    path('match/', include('matches.urls')),
    path('', lambda request: __import__('django.shortcuts', fromlist=['redirect']).redirect('dashboard'), name='home'),
]
