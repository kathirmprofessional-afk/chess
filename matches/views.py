from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q
import chess
import json
from .models import Match, Move, GameRoom, RoomInvite


# ─── Game Room Views ─────────────────────────────────────────────

@login_required
def create_room_view(request):
    """Create a new game room and redirect to lobby."""
    room = GameRoom.objects.create(host=request.user)
    return redirect('room_lobby', room_code=room.room_code)


@login_required
def join_room_view(request):
    """Join an existing room via invite code."""
    if request.method == 'POST':
        room_code = request.POST.get('room_code', '').strip().upper()
        try:
            room = GameRoom.objects.get(room_code=room_code)
        except GameRoom.DoesNotExist:
            messages.error(request, 'Invalid room code.')
            return redirect('dashboard')

        if room.status != 'waiting':
            messages.error(request, 'This room is no longer available.')
            return redirect('dashboard')

        if room.host == request.user:
            messages.info(request, 'You are the host of this room.')
            return redirect('room_lobby', room_code=room.room_code)

        if room.guest and room.guest != request.user:
            messages.error(request, 'This room is already full.')
            return redirect('dashboard')

        room.guest = request.user
        room.save()

        # Mark any invite for this room as accepted
        RoomInvite.objects.filter(
            room=room, invited_user=request.user, status='pending'
        ).update(status='accepted')

        return redirect('room_lobby', room_code=room.room_code)
    return redirect('dashboard')


@login_required
def room_lobby_view(request, room_code):
    """Show the room lobby where players wait for both to be ready."""
    room = get_object_or_404(GameRoom, room_code=room_code)

    if request.user != room.host and request.user != room.guest and room.status == 'waiting':
        # Not in the room yet — auto-join as guest
        if not room.guest:
            room.guest = request.user
            room.save()
            RoomInvite.objects.filter(
                room=room, invited_user=request.user, status='pending'
            ).update(status='accepted')
        else:
            messages.error(request, 'This room is full.')
            return redirect('dashboard')

    # If game is playing, redirect to the match
    if room.status == 'playing' and room.match:
        return redirect('match_detail', pk=room.match.pk)

    # Get host's friends for invite list
    friends = request.user.get_friends() if request.user == room.host else []

    # Filter out guest and users already invited
    invited_ids = set(room.invites.filter(status='pending').values_list('invited_user_id', flat=True))

    return render(request, 'matches/room_lobby.html', {
        'room': room,
        'friends': friends,
        'invited_ids': invited_ids,
    })


@login_required
@require_POST
def start_room_game_view(request, room_code):
    """Host starts the game — creates a Match and redirects to it."""
    room = get_object_or_404(GameRoom, room_code=room_code)

    if request.user != room.host:
        messages.error(request, 'Only the host can start the game.')
        return redirect('room_lobby', room_code=room_code)

    if not room.guest:
        messages.error(request, 'Waiting for an opponent to join.')
        return redirect('room_lobby', room_code=room_code)

    if room.status != 'waiting':
        if room.match:
            return redirect('match_detail', pk=room.match.pk)
        messages.error(request, 'Game already started or completed.')
        return redirect('room_lobby', room_code=room_code)

    # Create the match
    match = Match.objects.create(
        player1=room.host,
        player2=room.guest,
        status='active',
    )
    room.match = match
    room.status = 'playing'
    room.save()

    return redirect('match_detail', pk=match.pk)


@login_required
def room_status_api(request, room_code):
    """API to check room status (polling from lobby)."""
    room = get_object_or_404(GameRoom, room_code=room_code)
    return JsonResponse({
        'status': room.status,
        'host': room.host.username,
        'guest': room.guest.username if room.guest else None,
        'match_id': room.match_id,
    })


# ─── Room Invite Views ───────────────────────────────────────────

@login_required
@require_POST
def invite_friend_to_room_view(request, room_code, user_id):
    """Invite a friend to join the room."""
    room = get_object_or_404(GameRoom, room_code=room_code)
    from accounts.models import User
    invited_user = get_object_or_404(User, pk=user_id)

    if request.user != room.host:
        return JsonResponse({'success': False, 'message': 'Only the host can invite.'}, status=403)

    if room.status != 'waiting':
        return JsonResponse({'success': False, 'message': 'Room is not accepting players.'}, status=400)

    _, created = RoomInvite.objects.get_or_create(
        room=room, invited_user=invited_user,
        defaults={'invited_by': request.user}
    )

    if created:
        return JsonResponse({'success': True, 'message': f'Invite sent to {invited_user.username}!'})
    return JsonResponse({'success': True, 'message': f'{invited_user.username} already invited.'})


@login_required
@require_POST
def accept_room_invite_view(request, invite_id):
    """Accept a room invite — join the room."""
    invite = get_object_or_404(RoomInvite, pk=invite_id, invited_user=request.user, status='pending')
    room = invite.room

    if room.status != 'waiting':
        invite.status = 'declined'
        invite.save()
        messages.error(request, 'This room is no longer available.')
        return redirect('dashboard')

    if room.guest and room.guest != request.user:
        invite.status = 'declined'
        invite.save()
        messages.error(request, 'This room is already full.')
        return redirect('dashboard')

    room.guest = request.user
    room.save()
    invite.status = 'accepted'
    invite.save()

    return redirect('room_lobby', room_code=room.room_code)


@login_required
@require_POST
def decline_room_invite_view(request, invite_id):
    """Decline a room invite."""
    invite = get_object_or_404(RoomInvite, pk=invite_id, invited_user=request.user, status='pending')
    invite.status = 'declined'
    invite.save()
    messages.info(request, 'Room invite declined.')
    return redirect('dashboard')


@login_required
def pending_invites_api(request):
    """API endpoint returning pending room invites for the current user."""
    invites = RoomInvite.objects.filter(
        invited_user=request.user,
        status='pending',
        room__status='waiting'
    ).select_related('room', 'invited_by')

    return JsonResponse({'invites': [{
        'id': inv.id,
        'room_code': inv.room.room_code,
        'invited_by': inv.invited_by.username,
        'created_at': inv.created_at.isoformat(),
    } for inv in invites]})


# ─── Match Views (existing) ──────────────────────────────────────

@login_required
def match_detail_view(request, pk):
    match = get_object_or_404(Match.objects.select_related(
        'player1', 'player2', 'winner', 'tournament'
    ), pk=pk)

    moves = match.moves.select_related('player').all()
    is_player = request.user in [match.player1, match.player2]
    is_spectator = not is_player

    # Determine player color
    player_color = None
    if request.user == match.player1:
        player_color = 'white'
    elif request.user == match.player2:
        player_color = 'black'

    return render(request, 'matches/game.html', {
        'match': match,
        'moves': moves,
        'is_player': is_player,
        'is_spectator': is_spectator,
        'player_color': player_color,
    })


@login_required
def game_state_api(request, pk):
    """API endpoint to get the current game state."""
    match = get_object_or_404(Match.objects.select_related(
        'player1', 'player2', 'winner'
    ), pk=pk)

    moves = list(match.moves.order_by('timestamp').values_list('move_notation', flat=True))

    return JsonResponse({
        'fen': match.fen,
        'moves': moves,
        'status': match.status,
        'player1': match.player1.username if match.player1 else None,
        'player2': match.player2.username if match.player2 else None,
        'winner': match.winner.username if match.winner else None,
        'move_count': len(moves),
    })


@login_required
@require_POST
def make_move_api(request, pk):
    """API endpoint to make a move via AJAX."""
    match = get_object_or_404(Match.objects.select_related(
        'player1', 'player2', 'tournament'
    ), pk=pk)

    if match.status != 'active':
        return JsonResponse({'valid': False, 'message': 'Match is not active.'}, status=400)

    try:
        data = json.loads(request.body)
        move_uci = data.get('move', '')
    except (json.JSONDecodeError, AttributeError):
        move_uci = request.POST.get('move', '')

    if not move_uci:
        return JsonResponse({'valid': False, 'message': 'No move provided.'}, status=400)

    board = chess.Board(match.fen)

    # Validate turn
    is_white_turn = board.turn == chess.WHITE
    if is_white_turn and request.user != match.player1:
        return JsonResponse({'valid': False, 'message': 'Not your turn.'}, status=400)
    if not is_white_turn and request.user != match.player2:
        return JsonResponse({'valid': False, 'message': 'Not your turn.'}, status=400)

    # Validate and make move
    try:
        chess_move = chess.Move.from_uci(move_uci)
        if chess_move not in board.legal_moves:
            return JsonResponse({'valid': False, 'message': 'Illegal move.'}, status=400)
    except ValueError:
        return JsonResponse({'valid': False, 'message': 'Invalid move format.'}, status=400)

    # Get SAN before pushing
    san = board.san(chess_move)
    board.push(chess_move)
    new_fen = board.fen()

    # Save move
    Move.objects.create(
        match=match,
        player=request.user,
        move_notation=san,
        fen_after=new_fen,
    )

    match.fen = new_fen
    is_checkmate = board.is_checkmate()
    is_stalemate = board.is_stalemate()
    is_draw = is_stalemate or board.is_insufficient_material()

    result = {
        'valid': True,
        'fen': new_fen,
        'san': san,
        'is_checkmate': is_checkmate,
        'is_stalemate': is_stalemate,
        'is_draw': is_draw,
        'status': 'active',
        'winner': None,
    }

    if is_checkmate:
        match.winner = request.user
        match.status = 'completed'
        result['winner'] = request.user.username
        result['status'] = 'completed'
        if match.tournament:
            _advance_winner(match)
    elif is_draw or is_stalemate:
        match.winner = match.player1  # Simplified: white wins on draw
        match.status = 'completed'
        result['winner'] = match.player1.username
        result['status'] = 'completed'
        if match.tournament:
            _advance_winner(match)

    # Update room status if applicable
    if match.status == 'completed':
        try:
            room = match.game_room
            room.status = 'completed'
            room.save()
        except GameRoom.DoesNotExist:
            pass

    match.save()
    return JsonResponse(result)


@login_required
@require_POST
def resign_api(request, pk):
    """API endpoint to resign."""
    match = get_object_or_404(Match.objects.select_related(
        'player1', 'player2', 'tournament'
    ), pk=pk)

    if match.status != 'active':
        return JsonResponse({'error': 'Match is not active.'}, status=400)

    if request.user == match.player1:
        match.winner = match.player2
    elif request.user == match.player2:
        match.winner = match.player1
    else:
        return JsonResponse({'error': 'You are not a player in this match.'}, status=400)

    match.status = 'completed'
    match.save()

    if match.tournament:
        _advance_winner(match)

    # Update room status if applicable
    try:
        room = match.game_room
        room.status = 'completed'
        room.save()
    except GameRoom.DoesNotExist:
        pass

    return JsonResponse({
        'winner': match.winner.username,
        'status': 'completed',
    })


def _advance_winner(match):
    """Advance winner to next match in bracket."""
    from tournaments.views import advance_winner
    advance_winner(match)

    tournament = match.tournament
    remaining = tournament.matches.filter(status__in=['pending', 'active']).count()
    if remaining == 0:
        tournament.status = 'completed'
        tournament.save()
