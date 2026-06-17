from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

from game_manager import GameManager

app = FastAPI()
manager = GameManager()


@app.get("/")
def home():
    return {"message": "Bingo API Running"}


def get_all_boards(game):
    boards = {}

    for player in game.players:
        boards[player.name] = {
            "board": player.board.board,
            "marked": player.board.marked
        }

    return boards


def get_game_state(game):
    winner = game.get_winner()
    host_name = game.players[0].name if game.players else None

    return {
        "players": [p.name for p in game.players],
        "player_count": len(game.players),
        "max_players": 4,
        "called_numbers": game.called_numbers,
        "boards": get_all_boards(game),
        "scoreboard": game.get_scoreboard(),
        "current_turn": game.get_current_player().name if game.get_current_player() else None,
        "winner": winner.name if winner else None,
        "game_started": getattr(game, "game_started", False),
        "host": host_name
    }


class ConnectionManager:
    def __init__(self):
        self.rooms = {}

    async def connect(self, room_code: str, websocket: WebSocket):
        await websocket.accept()

        if room_code not in self.rooms:
            self.rooms[room_code] = []

        self.rooms[room_code].append(websocket)

    def disconnect(self, room_code: str, websocket: WebSocket):
        if room_code in self.rooms:
            if websocket in self.rooms[room_code]:
                self.rooms[room_code].remove(websocket)

    async def send_json(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_text(json.dumps(message))
        except:
            pass

    async def broadcast_json(self, room_code: str, message: dict):
        if room_code not in self.rooms:
            return

        active_connections = []

        for connection in self.rooms[room_code]:
            try:
                await connection.send_text(json.dumps(message))
                active_connections.append(connection)
            except:
                pass

        self.rooms[room_code] = active_connections


ws_manager = ConnectionManager()


@app.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    await ws_manager.connect(room_code, websocket)

    if not manager.room_exists(room_code):
        manager.create_room(room_code)

    game = manager.get_room(room_code)

    if not hasattr(game, "game_started"):
        game.game_started = False

    player_name = None

    try:
        await ws_manager.send_json(websocket, {
            "event": "connected",
            "message": f"Connected to room {room_code}"
        })

        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except:
                await ws_manager.send_json(websocket, {
                    "event": "error",
                    "message": "Invalid JSON"
                })
                continue

            event = message.get("event")

            # -----------------------------
            # JOIN ROOM
            # -----------------------------
            if event == "join":
                player_name = message.get("player_name")

                if not player_name:
                    await ws_manager.send_json(websocket, {
                        "event": "error",
                        "message": "Player name is required"
                    })
                    continue

                if len(game.players) >= 4:
                    await ws_manager.send_json(websocket, {
                        "event": "room_full",
                        "message": "Room already has 4 players"
                    })
                    continue

                if game.get_player(player_name):
                    await ws_manager.send_json(websocket, {
                        "event": "error",
                        "message": "Player name already exists"
                    })
                    continue

                game.add_player(player_name)
                player = game.get_player(player_name)

                host_name = game.players[0].name if game.players else None

                await ws_manager.send_json(websocket, {
                    "event": "your_board",
                    "player_name": player.name,
                    "board": player.board.board,
                    "marked": player.board.marked,
                    "is_host": player_name == host_name,
                    **get_game_state(game)
                })

                await ws_manager.broadcast_json(room_code, {
                    "event": "player_joined",
                    "player_name": player_name,
                    **get_game_state(game)
                })

            # -----------------------------
            # START GAME
            # -----------------------------
            elif event == "start_game":
                player_name = message.get("player_name")

                host_name = game.players[0].name if game.players else None

                if player_name != host_name:
                    await ws_manager.send_json(websocket, {
                        "event": "error",
                        "message": "Only host can start the game"
                    })
                    continue

                if len(game.players) < 2:
                    await ws_manager.send_json(websocket, {
                        "event": "error",
                        "message": "At least 2 players are needed to start"
                    })
                    continue

                game.game_started = True

                await ws_manager.broadcast_json(room_code, {
                    "event": "game_started",
                    **get_game_state(game)
                })

            # -----------------------------
            # CALL NUMBER
            # -----------------------------
            elif event == "call_number":
                if not game.game_started:
                    await ws_manager.send_json(websocket, {
                        "event": "error",
                        "message": "Game has not started yet"
                    })
                    continue

                player_name = message.get("player_name")
                number = message.get("number")

                if player_name is None or number is None:
                    await ws_manager.send_json(websocket, {
                        "event": "error",
                        "message": "player_name and number are required"
                    })
                    continue

                success, msg = game.call_number(player_name, int(number))

                if not success:
                    await ws_manager.send_json(websocket, {
                        "event": "error",
                        "message": msg
                    })
                    continue

                await ws_manager.broadcast_json(room_code, {
                    "event": "number_called",
                    "message": msg,
                    "number": int(number),
                    "called_by": player_name,
                    **get_game_state(game)
                })

            # -----------------------------
            # UNKNOWN EVENT
            # -----------------------------
            else:
                await ws_manager.send_json(websocket, {
                    "event": "error",
                    "message": "Unknown event"
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(room_code, websocket)
