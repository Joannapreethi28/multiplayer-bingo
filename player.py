from game.board import Board


class Player:
    def __init__(self, name):
        self.name = name
        self.board = Board()

    def get_completed_lines(self):
        return self.board.count_completed_lines()

    def get_bingo_letters(self):
        return self.board.get_bingo_letters()
