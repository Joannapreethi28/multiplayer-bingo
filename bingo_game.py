from player import Player
from board import Board


class BingoGame:
    def __init__(self, room_code):
        self.room_code = room_code
        self.players = []
        self.called_numbers = []
        self.current_turn = 0

    def add_player(self, name):
        self.players.append(Player(name))

    def remove_player(self, name):
        """Remove a player (e.g. on disconnect) and keep the turn index valid.

        Removing a player who sits before the current player would shift every
        later index down by one, so we adjust current_turn to keep pointing at
        the same person. If the current player is removed, the turn naturally
        falls to whoever now occupies that slot.
        """
        index = None
        for i, player in enumerate(self.players):
            if player.name == name:
                index = i
                break

        if index is None:
            return False

        self.players.pop(index)

        if not self.players:
            self.current_turn = 0
            return True
