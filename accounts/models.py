from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    rating = models.IntegerField(default=1200)

    def __str__(self):
        return f"{self.username} ({self.rating})"

    def get_friends(self):
        """Return queryset of all friends for this user."""
        from django.db.models import Q
        friendships = Friendship.objects.filter(Q(user1=self) | Q(user2=self))
        friend_ids = []
        for f in friendships:
            friend_ids.append(f.user2_id if f.user1_id == self.id else f.user1_id)
        return User.objects.filter(id__in=friend_ids)


class FriendRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username} ({self.status})"


class Friendship(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_as_user2')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')

    def __str__(self):
        return f"{self.user1.username} ↔ {self.user2.username}"
