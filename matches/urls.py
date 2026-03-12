from django.urls import path
from . import views

urlpatterns = [
    # Room system
    path('room/create/', views.create_room_view, name='create_room'),
    path('room/join/', views.join_room_view, name='join_room'),
    path('room/<str:room_code>/', views.room_lobby_view, name='room_lobby'),
    path('room/<str:room_code>/start/', views.start_room_game_view, name='start_room_game'),
    path('room/<str:room_code>/status/', views.room_status_api, name='room_status_api'),
    path('room/<str:room_code>/invite/<int:user_id>/', views.invite_friend_to_room_view, name='invite_friend_to_room'),

    # Room invites
    path('invite/<int:invite_id>/accept/', views.accept_room_invite_view, name='accept_room_invite'),
    path('invite/<int:invite_id>/decline/', views.decline_room_invite_view, name='decline_room_invite'),
    path('api/invites/', views.pending_invites_api, name='pending_invites_api'),

    # Match game
    path('<int:pk>/', views.match_detail_view, name='match_detail'),
    path('<int:pk>/api/state/', views.game_state_api, name='game_state_api'),
    path('<int:pk>/api/move/', views.make_move_api, name='make_move_api'),
    path('<int:pk>/api/resign/', views.resign_api, name='resign_api'),
]
