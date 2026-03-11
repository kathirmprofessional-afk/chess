from django.db import models
from django.conf import settings
import random
import string

def generate_invite_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

class Tournament(models.Model):
    STATUS_CHOICES = (
        ('waiting', 'Waiting for Players'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )

    name = models.CharField(max_length=100)
    invite_code = models.CharField(max_length=8, unique=True, default=generate_invite_code)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_tournaments')
    max_players = models.IntegerField(default=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.invite_code})"

class Player(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='players')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tournament')

    def __str__(self):
        return f"{self.user.username} in {self.tournament.name}"
