import random
import string
from django.db import models
from django.conf import settings
from tournaments.models import Tournament


def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class GameRoom(models.Model):
    STATUS_CHOICES = (
        ('waiting', 'Waiting for Opponent'),
        ('playing', 'Game in Progress'),
        ('completed', 'Completed'),
    )

    room_code = models.CharField(max_length=6, unique=True, default=generate_room_code)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_rooms')
    guest = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='joined_rooms')
    match = models.OneToOneField('Match', on_delete=models.SET_NULL, null=True, blank=True, related_name='game_room')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        guest_name = self.guest.username if self.guest else "Waiting..."
        return f"Room {self.room_code}: {self.host.username} vs {guest_name}"


class RoomInvite(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    )

    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name='invites')
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_room_invites')
    invited_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_room_invites')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('room', 'invited_user')
        ordering = ['-created_at']

    def __str__(self):
        return f"Invite: {self.invited_by.username} → {self.invited_user.username} for Room {self.room.room_code}"


class Match(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    )

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='matches', null=True, blank=True)
    player1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches_as_p1')
    player2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches_as_p2')
    winner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches_won')
    round_number = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    next_match = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_matches')

    fen = models.CharField(max_length=100, default='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')

    def __str__(self):
        p1 = self.player1.username if self.player1 else "TBD"
        p2 = self.player2.username if self.player2 else "TBD"
        if self.tournament:
            return f"{self.tournament.name} - R{self.round_number}: {p1} vs {p2}"
        return f"Room Game: {p1} vs {p2}"


class Move(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='moves')
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    move_notation = models.CharField(max_length=10)
    fen_after = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Match {self.match.id} - {self.player.username}: {self.move_notation}"
