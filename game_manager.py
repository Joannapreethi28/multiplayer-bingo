from game.bingo_game import BingoGame


class GameManager:
    def __init__(self):
        self.rooms = {}

    def create_room(self, room_code):
        if room_code in self.rooms:
            return None

        game = BingoGame(room_code)
        self.rooms[room_code] = game

        return game

    def get_room(self, room_code):
        return self.rooms.get(room_code)

    def room_exists(self, room_code):
        return room_code in self.rooms
