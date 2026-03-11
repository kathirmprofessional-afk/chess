from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import chess
import json
from .models import Match, Move


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
        _advance_winner(match)
    elif is_draw or is_stalemate:
        match.winner = match.player1  # Simplified: white wins on draw
        match.status = 'completed'
        result['winner'] = match.player1.username
        result['status'] = 'completed'
        _advance_winner(match)

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
    _advance_winner(match)

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
