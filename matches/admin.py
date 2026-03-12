from django.contrib import admin
from .models import GameRoom, RoomInvite, Match, Move


@admin.register(GameRoom)
class GameRoomAdmin(admin.ModelAdmin):
    list_display = ('room_code', 'host', 'guest', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(RoomInvite)
class RoomInviteAdmin(admin.ModelAdmin):
    list_display = ('room', 'invited_by', 'invited_user', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'player1', 'player2', 'status', 'winner')
    list_filter = ('status',)


@admin.register(Move)
class MoveAdmin(admin.ModelAdmin):
    list_display = ('match', 'player', 'move_notation', 'timestamp')
