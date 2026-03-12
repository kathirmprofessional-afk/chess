from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Friends
    path('friends/', views.friends_list_view, name='friends_list'),
    path('friends/search/', views.search_users_view, name='search_users'),
    path('friends/request/<int:user_id>/', views.send_friend_request_view, name='send_friend_request'),
    path('friends/accept/<int:request_id>/', views.accept_friend_request_view, name='accept_friend_request'),
    path('friends/reject/<int:request_id>/', views.reject_friend_request_view, name='reject_friend_request'),
    path('friends/remove/<int:user_id>/', views.remove_friend_view, name='remove_friend'),
]
