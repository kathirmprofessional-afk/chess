import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .forms import RegisterForm
from .models import User, FriendRequest, Friendship
from matches.models import Match


@csrf_exempt
def api_login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST
        username = data.get('username', '')
        password = data.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'rating': user.rating,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid username/email or password.'
            }, status=401)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def api_register_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST
        username = data.get('username', '')
        email = data.get('email', '')
        password = data.get('password', '')

        if not username or not email or not password:
            return JsonResponse({
                'success': False,
                'message': 'Username, email, and password are required.'
            }, status=400)

        if User.objects.filter(username__iexact=username).exists():
            return JsonResponse({
                'success': False,
                'message': 'Username already taken.'
            }, status=400)
        
        if User.objects.filter(email__iexact=email).exists():
            return JsonResponse({
                'success': False,
                'message': 'Email already registered.'
            }, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user, backend='accounts.backends.EmailOrUsernameModelBackend')
        return JsonResponse({
            'success': True,
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'rating': user.rating,
            }
        })
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='accounts.backends.EmailOrUsernameModelBackend')
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    user = request.user
    matches_played = Match.objects.filter(
        Q(player1=user) | Q(player2=user),
        status='completed'
    ).count()
    matches_won = Match.objects.filter(winner=user).count()
    context = {
        'user': user,
        'matches_played': matches_played,
        'matches_won': matches_won,
    }
    return render(request, 'accounts/profile.html', context)


# ─── Friend System ───────────────────────────────────────────────

@login_required
def friends_list_view(request):
    """Main friends page: friends list, pending requests, search."""
    user = request.user
    friends = user.get_friends()

    incoming_requests = FriendRequest.objects.filter(
        to_user=user, status='pending'
    ).select_related('from_user')

    outgoing_requests = FriendRequest.objects.filter(
        from_user=user, status='pending'
    ).select_related('to_user')

    return render(request, 'accounts/friends.html', {
        'friends': friends,
        'incoming_requests': incoming_requests,
        'outgoing_requests': outgoing_requests,
    })


@login_required
def search_users_view(request):
    """AJAX endpoint to search users by username."""
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'users': []})

    users = User.objects.filter(
        username__icontains=query
    ).exclude(id=request.user.id)[:10]

    # Check existing relationships
    user = request.user
    friend_ids = set(user.get_friends().values_list('id', flat=True))
    pending_sent = set(FriendRequest.objects.filter(
        from_user=user, status='pending'
    ).values_list('to_user_id', flat=True))
    pending_received = set(FriendRequest.objects.filter(
        to_user=user, status='pending'
    ).values_list('from_user_id', flat=True))

    results = []
    for u in users:
        status = 'none'
        if u.id in friend_ids:
            status = 'friend'
        elif u.id in pending_sent:
            status = 'request_sent'
        elif u.id in pending_received:
            status = 'request_received'
        results.append({
            'id': u.id,
            'username': u.username,
            'rating': u.rating,
            'status': status,
        })

    return JsonResponse({'users': results})


@login_required
@require_POST
def send_friend_request_view(request, user_id):
    """Send a friend request to another user."""
    to_user = get_object_or_404(User, pk=user_id)

    if to_user == request.user:
        return JsonResponse({'success': False, 'message': 'Cannot send request to yourself.'}, status=400)

    # Check if already friends
    if Friendship.objects.filter(
        Q(user1=request.user, user2=to_user) | Q(user1=to_user, user2=request.user)
    ).exists():
        return JsonResponse({'success': False, 'message': 'Already friends.'}, status=400)

    # Check if request already exists
    existing = FriendRequest.objects.filter(from_user=request.user, to_user=to_user).first()
    if existing:
        if existing.status == 'pending':
            return JsonResponse({'success': False, 'message': 'Request already sent.'}, status=400)
        elif existing.status == 'rejected':
            existing.status = 'pending'
            existing.save()
            return JsonResponse({'success': True, 'message': f'Friend request re-sent to {to_user.username}!'})

    # Check if the other user sent us a request — auto-accept
    reverse_request = FriendRequest.objects.filter(from_user=to_user, to_user=request.user, status='pending').first()
    if reverse_request:
        reverse_request.status = 'accepted'
        reverse_request.save()
        Friendship.objects.create(user1=request.user, user2=to_user)
        return JsonResponse({'success': True, 'message': f'You and {to_user.username} are now friends!'})

    FriendRequest.objects.create(from_user=request.user, to_user=to_user)
    return JsonResponse({'success': True, 'message': f'Friend request sent to {to_user.username}!'})


@login_required
@require_POST
def accept_friend_request_view(request, request_id):
    """Accept an incoming friend request."""
    freq = get_object_or_404(FriendRequest, pk=request_id, to_user=request.user, status='pending')
    freq.status = 'accepted'
    freq.save()

    # Create the friendship (order by id to avoid duplicates)
    u1, u2 = (freq.from_user, freq.to_user) if freq.from_user_id < freq.to_user_id else (freq.to_user, freq.from_user)
    Friendship.objects.get_or_create(user1=u1, user2=u2)

    messages.success(request, f'You are now friends with {freq.from_user.username}!')
    return redirect('friends_list')


@login_required
@require_POST
def reject_friend_request_view(request, request_id):
    """Reject an incoming friend request."""
    freq = get_object_or_404(FriendRequest, pk=request_id, to_user=request.user, status='pending')
    freq.status = 'rejected'
    freq.save()
    messages.info(request, f'Friend request from {freq.from_user.username} rejected.')
    return redirect('friends_list')


@login_required
@require_POST
def remove_friend_view(request, user_id):
    """Remove a friend."""
    other_user = get_object_or_404(User, pk=user_id)
    Friendship.objects.filter(
        Q(user1=request.user, user2=other_user) | Q(user1=other_user, user2=request.user)
    ).delete()
    messages.info(request, f'{other_user.username} removed from friends.')
    return redirect('friends_list')
