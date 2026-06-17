import random


class Board:
    def __init__(self):
        self.board = self.generate_board()
        self.marked = [[False for _ in range(5)] for _ in range(5)]

    def generate_board(self):
        numbers = list(range(1, 26))
        random.shuffle(numbers)

        board = []

        for i in range(5):
            row = numbers[i * 5:(i + 1) * 5]
            board.append(row)

        return board

    def mark_number(self, number):
        for row in range(5):
            for col in range(5):
                if self.board[row][col] == number:
                    self.marked[row][col] = True

    def count_completed_lines(self):
        completed_lines = 0

        # Check rows
        for row in self.marked:
            if all(row):
                completed_lines += 1

        # Check columns
        for col in range(5):
            if all(self.marked[row][col] for row in range(5)):
                completed_lines += 1

        return completed_lines

    def get_bingo_letters(self):
        letters = "BINGO"
        completed = self.count_completed_lines()

        if completed >= 5:
            return "BINGO"

        return letters[:completed]

    def display_board(self):
        for row in self.board:
            print(row)

    def display_marked(self):
        for row in self.marked:
            print(row)

    # Temporary testing helper
    def mark_row(self, row_number):
        for col in range(5):
            self.marked[row_number][col] = True
