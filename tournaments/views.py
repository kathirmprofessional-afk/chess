import math
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Tournament, Player
from matches.models import Match


@login_required
def dashboard_view(request):
    my_tournaments = Tournament.objects.filter(players__user=request.user).order_by('-created_at')
    hosted_tournaments = Tournament.objects.filter(host=request.user).order_by('-created_at')
    
    from matches.models import RoomInvite, GameRoom
    from django.db.models import Q
    
    pending_room_invites = RoomInvite.objects.filter(
        invited_user=request.user, 
        status='pending',
        room__status='waiting'
    ).order_by('-created_at')

    active_rooms = GameRoom.objects.filter(
        Q(host=request.user) | Q(guest=request.user),
        status__in=['waiting', 'playing']
    ).order_by('-created_at')
    
    return render(request, 'tournaments/dashboard.html', {
        'my_tournaments': my_tournaments,
        'hosted_tournaments': hosted_tournaments,
        'pending_room_invites': pending_room_invites,
        'active_rooms': active_rooms,
    })


@login_required
def create_tournament_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        max_players = int(request.POST.get('max_players', 8))
        tournament = Tournament.objects.create(
            name=name,
            host=request.user,
            max_players=max_players,
        )
        # Host automatically joins as a player
        Player.objects.create(user=request.user, tournament=tournament)
        messages.success(request, f'Tournament created! Invite code: {tournament.invite_code}')
        return redirect('tournament_detail', pk=tournament.pk)
    return render(request, 'tournaments/create.html')


@login_required
def join_tournament_view(request):
    if request.method == 'POST':
        invite_code = request.POST.get('invite_code', '').strip().upper()
        try:
            tournament = Tournament.objects.get(invite_code=invite_code)
        except Tournament.DoesNotExist:
            messages.error(request, 'Invalid invite code.')
            return redirect('dashboard')

        if tournament.status != 'waiting':
            messages.error(request, 'This tournament has already started.')
            return redirect('dashboard')

        if tournament.players.count() >= tournament.max_players:
            messages.error(request, 'This tournament is full.')
            return redirect('dashboard')

        if Player.objects.filter(user=request.user, tournament=tournament).exists():
            messages.info(request, 'You are already in this tournament.')
        else:
            Player.objects.create(user=request.user, tournament=tournament)
            messages.success(request, f'Joined tournament: {tournament.name}!')

        return redirect('tournament_detail', pk=tournament.pk)
    return redirect('dashboard')


@login_required
def tournament_detail_view(request, pk):
    tournament = get_object_or_404(Tournament, pk=pk)
    players = tournament.players.select_related('user').all()
    matches = tournament.matches.select_related('player1', 'player2', 'winner').order_by('round_number', 'id')
    is_host = request.user == tournament.host
    is_player = players.filter(user=request.user).exists()

    total_rounds = 0
    if matches.exists():
        total_rounds = matches.last().round_number

    rounds = {}
    for match in matches:
        r = match.round_number
        if r not in rounds:
            rounds[r] = []
        rounds[r].append(match)

    return render(request, 'tournaments/detail.html', {
        'tournament': tournament,
        'players': players,
        'matches': matches,
        'rounds': rounds,
        'total_rounds': total_rounds,
        'is_host': is_host,
        'is_player': is_player,
    })


@login_required
def start_tournament_view(request, pk):
    tournament = get_object_or_404(Tournament, pk=pk)

    if request.user != tournament.host:
        messages.error(request, 'Only the host can start the tournament.')
        return redirect('tournament_detail', pk=pk)

    if tournament.status != 'waiting':
        messages.error(request, 'Tournament has already been started.')
        return redirect('tournament_detail', pk=pk)

    player_list = list(tournament.players.select_related('user').all())
    if len(player_list) < 2:
        messages.error(request, 'Need at least 2 players to start.')
        return redirect('tournament_detail', pk=pk)

    random.shuffle(player_list)
    generate_bracket(tournament, player_list)
    tournament.status = 'in_progress'
    tournament.save()

    messages.success(request, 'Tournament started! Bracket generated.')
    return redirect('tournament_detail', pk=pk)


def generate_bracket(tournament, player_list):
    """
    Generate a single-elimination bracket.
    Handles byes for non-power-of-two player counts.
    """
    num_players = len(player_list)
    # Find next power of 2
    total_slots = 1
    while total_slots < num_players:
        total_slots *= 2

    total_rounds = int(math.log2(total_slots))
    num_byes = total_slots - num_players

    # Create all match slots for the entire bracket (bottom-up)
    # We create matches for each round, linking them to their next-round match.
    matches_by_round = {}

    # Create matches from the final round down to round 1
    for r in range(total_rounds, 0, -1):
        num_matches_in_round = total_slots // (2 ** r)
        matches_by_round[r] = []
        for i in range(num_matches_in_round):
            next_match = None
            if r < total_rounds:
                # This match feeds into a match in the next round
                pass  # We'll link after creation

            match = Match.objects.create(
                tournament=tournament,
                round_number=r,
                status='pending',
            )
            matches_by_round[r].append(match)

    # Link matches to their next round
    for r in range(1, total_rounds):
        for i, match in enumerate(matches_by_round[r]):
            next_match_index = i // 2
            match.next_match = matches_by_round[r + 1][next_match_index]
            match.save()

    # Assign players to round 1 matches
    round_1_matches = matches_by_round[1]
    player_idx = 0

    for i, match in enumerate(round_1_matches):
        if player_idx < num_players:
            match.player1 = player_list[player_idx].user
            player_idx += 1

        if player_idx < num_players:
            match.player2 = player_list[player_idx].user
            player_idx += 1

        match.save()

    # Handle byes: if a match has only one player, auto-advance them
    for match in round_1_matches:
        if match.player1 and not match.player2:
            match.winner = match.player1
            match.status = 'completed'
            match.save()
            advance_winner(match)
        elif match.player2 and not match.player1:
            match.winner = match.player2
            match.status = 'completed'
            match.save()
            advance_winner(match)
        elif match.player1 and match.player2:
            match.status = 'active'
            match.save()


def advance_winner(match):
    """Advance the winner of a match to the next round."""
    if not match.next_match or not match.winner:
        return

    next_match = match.next_match
    if not next_match.player1:
        next_match.player1 = match.winner
    elif not next_match.player2:
        next_match.player2 = match.winner
    next_match.save()

    # If both players are set in the next match, activate it
    if next_match.player1 and next_match.player2:
        next_match.status = 'active'
        next_match.save()
    # If only one player due to bye opponent, check if the other feeder is also done
    elif next_match.player1 or next_match.player2:
        feeders = next_match.previous_matches.all()
        all_done = all(f.status == 'completed' for f in feeders)
        if all_done and feeders.count() == 2:
            # The other feeder had a bye - this player gets auto-advanced
            player = next_match.player1 or next_match.player2
            next_match.winner = player
            next_match.status = 'completed'
            next_match.save()
            advance_winner(next_match)


@login_required
def champion_view(request, pk):
    tournament = get_object_or_404(Tournament, pk=pk)
    final_match = tournament.matches.order_by('-round_number').first()
    champion = final_match.winner if final_match else None
    
    # Get all players with rankings
    all_matches = tournament.matches.filter(status='completed').select_related('winner', 'player1', 'player2')

    return render(request, 'tournaments/champion.html', {
        'tournament': tournament,
        'champion': champion,
        'final_match': final_match,
    })
