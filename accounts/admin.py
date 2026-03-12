from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, FriendRequest, Friendship


admin.site.register(User, UserAdmin)


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('user1', 'user2', 'created_at')
