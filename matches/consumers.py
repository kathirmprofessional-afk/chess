import json
import chess
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Match, Move


class ChessGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        self.room_group_name = f'match_{self.match_id}'
        self.user = self.scope['user']

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Send current game state on connect
        match_data = await self.get_match_state()
        await self.send(text_data=json.dumps({
            'type': 'game_state',
            'fen': match_data['fen'],
            'moves': match_data['moves'],
            'status': match_data['status'],
            'player1': match_data['player1'],
            'player2': match_data['player2'],
            'winner': match_data['winner'],
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'make_move':
            move_uci = data.get('move')
            result = await self.process_move(move_uci)

            if result['valid']:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'move_made',
                        'move': move_uci,
                        'fen': result['fen'],
                        'player': self.user.username,
                        'is_checkmate': result['is_checkmate'],
                        'is_stalemate': result['is_stalemate'],
                        'is_draw': result['is_draw'],
                        'winner': result.get('winner'),
                        'status': result['status'],
                    }
                )
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': result.get('message', 'Invalid move'),
                }))

        elif action == 'resign':
            result = await self.process_resign()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_over',
                    'reason': 'resignation',
                    'winner': result['winner'],
                }
            )

    async def move_made(self, event):
        await self.send(text_data=json.dumps({
            'type': 'move_made',
            'move': event['move'],
            'fen': event['fen'],
            'player': event['player'],
            'is_checkmate': event['is_checkmate'],
            'is_stalemate': event['is_stalemate'],
            'is_draw': event['is_draw'],
            'winner': event.get('winner'),
            'status': event['status'],
        }))

    async def game_over(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_over',
            'reason': event['reason'],
            'winner': event['winner'],
        }))

    @database_sync_to_async
    def get_match_state(self):
        match = Match.objects.select_related('player1', 'player2', 'winner').get(pk=self.match_id)
        moves = list(match.moves.values_list('move_notation', flat=True))
        return {
            'fen': match.fen,
            'moves': moves,
            'status': match.status,
            'player1': match.player1.username if match.player1 else None,
            'player2': match.player2.username if match.player2 else None,
            'winner': match.winner.username if match.winner else None,
        }

    @database_sync_to_async
    def process_move(self, move_uci):
        match = Match.objects.select_related('player1', 'player2', 'tournament').get(pk=self.match_id)

        if match.status != 'active':
            return {'valid': False, 'message': 'Match is not active.'}

        board = chess.Board(match.fen)

        # Validate turn
        is_white_turn = board.turn == chess.WHITE
        if is_white_turn and self.user != match.player1:
            return {'valid': False, 'message': 'Not your turn.'}
        if not is_white_turn and self.user != match.player2:
            return {'valid': False, 'message': 'Not your turn.'}

        # Validate and make move
        try:
            chess_move = chess.Move.from_uci(move_uci)
            if chess_move not in board.legal_moves:
                return {'valid': False, 'message': 'Illegal move.'}
        except ValueError:
            return {'valid': False, 'message': 'Invalid move format.'}

        # Get SAN before pushing (for notation display)
        san = board.san(chess_move)
        board.push(chess_move)
        new_fen = board.fen()

        # Save move
        Move.objects.create(
            match=match,
            player=self.user,
            move_notation=san,
            fen_after=new_fen,
        )

        match.fen = new_fen
        result = {
            'valid': True,
            'fen': new_fen,
            'is_checkmate': board.is_checkmate(),
            'is_stalemate': board.is_stalemate(),
            'is_draw': board.is_stalemate() or board.is_insufficient_material() or board.can_claim_fifty_moves(),
            'status': 'active',
        }

        if board.is_checkmate():
            match.winner = self.user
            match.status = 'completed'
            result['winner'] = self.user.username
            result['status'] = 'completed'
            # Advance winner in tournament bracket
            self._advance_winner_sync(match)
        elif result['is_draw'] or board.is_stalemate():
            # In tournament play, draw means white wins (simplified rule)
            match.winner = match.player1
            match.status = 'completed'
            result['winner'] = match.player1.username
            result['status'] = 'completed'
            self._advance_winner_sync(match)

        match.save()
        return result

    def _advance_winner_sync(self, match):
        """Advance winner to next match in bracket."""
        from tournaments.views import advance_winner
        advance_winner(match)

        # Check if tournament is complete
        tournament = match.tournament
        remaining = tournament.matches.filter(status__in=['pending', 'active']).count()
        if remaining == 0:
            tournament.status = 'completed'
            tournament.save()

    @database_sync_to_async
    def process_resign(self):
        match = Match.objects.select_related('player1', 'player2', 'tournament').get(pk=self.match_id)

        if self.user == match.player1:
            match.winner = match.player2
        else:
            match.winner = match.player1

        match.status = 'completed'
        match.save()

        self._advance_winner_sync(match)

        return {'winner': match.winner.username}
