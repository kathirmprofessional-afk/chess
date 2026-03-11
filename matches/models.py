from django.db import models
from django.conf import settings
from tournaments.models import Tournament

class Match(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    )

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='matches')
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
        return f"{self.tournament.name} - R{self.round_number}: {p1} vs {p2}"

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
