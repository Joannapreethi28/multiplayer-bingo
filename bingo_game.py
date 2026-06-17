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

        if index < self.current_turn:
            self.current_turn -= 1

        # Clamp in case we removed the last player in the list while it was
        # their turn.
        self.current_turn %= len(self.players)
        return True

    def reset(self):
        """Start a fresh round: new boards, no called numbers, host goes first."""
        self.called_numbers = []
        self.current_turn = 0
        for player in self.players:
            player.board = Board()

    def get_player(self, name):
        for player in self.players:
            if player.name == name:
                return player
        return None

    def get_current_player(self):
        if not self.players:
            return None

        return self.players[self.current_turn]

    def next_turn(self):
        if self.players:
            self.current_turn = (self.current_turn + 1) % len(self.players)

    def call_number(self, player_name, number):
        current_player = self.get_current_player()

        if current_player is None:
            return False, "No players in game"

        if current_player.name != player_name:
            return False, "Not your turn"

        if number in self.called_numbers:
            return False, "Number already called"

        player = self.get_player(player_name)

        if player is None:
            return False, "Player not found"

        number_exists = False

        for row in player.board.board:
            if number in row:
                number_exists = True
                break

        if not number_exists:
            return False, "Number not on your board"

        self.called_numbers.append(number)

        for p in self.players:
            p.board.mark_number(number)

        self.next_turn()

        return True, "Number called successfully"

    def get_winner(self):
        for player in self.players:
            if player.get_bingo_letters() == "BINGO":
                return player

        return None

    def show_scoreboard(self):
        print("\n===== SCOREBOARD =====")

        for player in self.players:
            print(
                f"{player.name}: "
                f"{player.get_completed_lines()} lines "
                f"({player.get_bingo_letters()})"
            )

    def get_scoreboard(self):
        scoreboard = []

        for player in self.players:
            scoreboard.append(
                {
                    "name": player.name,
                    "lines": player.get_completed_lines(),
                    "letters": player.get_bingo_letters()
                }
            )

        return scoreboard
