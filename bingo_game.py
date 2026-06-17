from game.player import Player


class BingoGame:
    def __init__(self, room_code):
        self.room_code = room_code
        self.players = []
        self.called_numbers = []
        self.current_turn = 0

    def add_player(self, name):
        self.players.append(Player(name))

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

        print("========== TURN DEBUG ==========")
        print("Room Code:", self.room_code)
        print("Current Turn Index:", self.current_turn)

        if current_player:
            print("Current Player:", current_player.name)
        else:
            print("Current Player: None")

        print("Player Request:", player_name)
        print("Players In Room:", [p.name for p in self.players])
        print("Called Numbers:", self.called_numbers)
        print("================================")

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
