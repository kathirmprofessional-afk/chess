from accounts.models import FriendRequest
from matches.models import RoomInvite


def notifications(request):
    """Add pending friend request and room invite counts to all templates."""
    if request.user.is_authenticated:
        pending_friend_count = FriendRequest.objects.filter(
            to_user=request.user, status='pending'
        ).count()
        pending_invite_count = RoomInvite.objects.filter(
            invited_user=request.user, status='pending',
            room__status='waiting'
        ).count()
        return {
            'pending_friend_count': pending_friend_count,
            'pending_invite_count': pending_invite_count,
        }
    return {}
