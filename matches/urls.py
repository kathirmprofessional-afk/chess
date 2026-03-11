from django.urls import path
from . import views

urlpatterns = [
    path('<int:pk>/', views.match_detail_view, name='match_detail'),
    path('<int:pk>/api/state/', views.game_state_api, name='game_state_api'),
    path('<int:pk>/api/move/', views.make_move_api, name='make_move_api'),
    path('<int:pk>/api/resign/', views.resign_api, name='resign_api'),
]
