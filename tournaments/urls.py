from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('create/', views.create_tournament_view, name='create_tournament'),
    path('join/', views.join_tournament_view, name='join_tournament'),
    path('<int:pk>/', views.tournament_detail_view, name='tournament_detail'),
    path('<int:pk>/start/', views.start_tournament_view, name='start_tournament'),
    path('<int:pk>/champion/', views.champion_view, name='champion'),
]
