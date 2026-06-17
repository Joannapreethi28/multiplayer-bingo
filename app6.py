import streamlit as st
import websocket
import json
import random
import string
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Multiplayer Bingo",
    page_icon="🎯",
    layout="wide"
)

BACKEND_URL = "wss://bingo-backend-2o3a.onrender.com/ws"


defaults = {
    "connected": False,
    "ws": None,
    "player_name": "",
    "room_code": "",
    "game_started": False,
    "players": [],
    "board": None,
    "marked": None,
    "called_numbers": [],
    "scoreboard": [],
    "current_turn": None,
    "winner": None,
    "celebrated": False
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


if "room" in st.query_params and st.session_state.room_code == "":
    st.session_state.room_code = st.query_params["room"]


st.markdown(
    """
    <style>
    .main-title {
        text-align: center;
        font-size: 45px;
        font-weight: 800;
        color: #6C63FF;
    }

    .subtitle {
        text-align: center;
        font-size: 18px;
        color: #777;
        margin-bottom: 30px;
    }

    .card {
        background: white;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #e8e8e8;
        box-shadow: 0 3px 10px rgba(0,0,0,0.08);
        text-align: center;
        margin-bottom: 12px;
    }

    .join-card {
        background: linear-gradient(135deg, #6C63FF, #8E7CFF);
        padding: 25px;
        border-radius: 18px;
        color: white;
        text-align: center;
    }

    .winner-box {
        background: linear-gradient(135deg, #FFD700, #FFA500);
        padding: 25px;
        border-radius: 20px;
        text-align: center;
        color: #222;
        font-size: 30px;
        font-weight: 800;
        margin-bottom: 20px;
    }

    .marked-cell {
        min-height: 48px;
        border-radius: 10px;
        background: linear-gradient(135deg, #00C853, #64DD17);
        color: white;
        font-size: 18px;
        font-weight: 800;
        text-align: center;
        padding-top: 12px;
        text-decoration: line-through;
        margin-bottom: 6px;
    }

    div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 48px;
        font-size: 18px;
        font-weight: 800;
        border-radius: 10px;
    }

    .turn-alert {
        background: #E8F5E9;
        color: #1B5E20;
        padding: 14px;
        border-radius: 12px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 15px;
    }

    .wait-alert {
        background: #FFF3E0;
        color: #E65100;
        padding: 14px;
        border-radius: 12px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 15px;
    }

    .letter-row {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-top: 8px;
        margin-bottom: 8px;
    }

    .letter-done {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background: #00C853;
        color: white;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        text-decoration: line-through;
    }

    .letter-pending {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background: #eeeeee;
        color: #777;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* MOBILE FIX */
    @media screen and (max-width: 600px) {
        .main-title {
            font-size: 32px;
        }

        .subtitle {
            font-size: 14px;
        }

        section.main > div {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }

        div[data-testid="column"] {
            min-width: 19% !important;
            width: 19% !important;
            flex: 1 1 19% !important;
        }

        div[data-testid="stButton"] > button {
            min-height: 42px;
            font-size: 15px;
            padding: 2px;
        }

        .marked-cell {
            min-height: 42px;
            font-size: 15px;
            padding-top: 10px;
        }

        .card {
            padding: 12px;
        }

        .card h2 {
            font-size: 18px;
        }

        .card h3 {
            font-size: 15px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def get_ws_url(room_code):
    return f"{BACKEND_URL}/{room_code}"


def wait_for_event(ws, wanted_events):
    while True:
        response = json.loads(ws.recv())

        if response["event"] in wanted_events:
            return response


def update_from_response(response):
    if "players" in response:
        st.session_state.players = response["players"]

    if "game_started" in response:
        st.session_state.game_started = response["game_started"]

    if "called_numbers" in response:
        st.session_state.called_numbers = response["called_numbers"]

    if "scoreboard" in response:
        st.session_state.scoreboard = response["scoreboard"]

    if "current_turn" in response:
        st.session_state.current_turn = response["current_turn"]

    if "winner" in response:
        st.session_state.winner = response["winner"]

    if "boards" in response:
        name = st.session_state.player_name

        if name in response["boards"]:
            st.session_state.board = response["boards"][name]["board"]
            st.session_state.marked = response["boards"][name]["marked"]


def auto_receive_updates():
    if st.session_state.connected and st.session_state.ws is not None:
        st.session_state.ws.settimeout(0.1)

        try:
            while True:
                response = json.loads(st.session_state.ws.recv())
                update_from_response(response)
        except:
            pass

        st.session_state.ws.settimeout(None)


def get_host_name():
    if st.session_state.players:
        return st.session_state.players[0]
    return None


def is_current_user_host():
    return st.session_state.player_name == get_host_name()


def send_start_game():
    message = {
        "event": "start_game",
        "player_name": st.session_state.player_name
    }

    st.session_state.ws.send(json.dumps(message))

    response = wait_for_event(
        st.session_state.ws,
        ["game_started", "error"]
    )

    update_from_response(response)

    if response["event"] == "error":
        st.error(response["message"])

    st.rerun()


def call_number(number):
    message = {
        "event": "call_number",
        "player_name": st.session_state.player_name,
        "number": int(number)
    }

    st.session_state.ws.send(json.dumps(message))

    response = wait_for_event(
        st.session_state.ws,
        ["number_called", "error"]
    )

    update_from_response(response)

    if response["event"] == "error":
        st.error(response["message"])

    st.rerun()


def render_board(board, marked):
    is_my_turn = st.session_state.current_turn == st.session_state.player_name
    game_over = st.session_state.winner is not None
    can_click = is_my_turn and not game_over and st.session_state.game_started

    st.markdown(
        """
        <style>
        .bingo-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 6px;
            width: 100%;
            max-width: 420px;
            margin: auto;
        }

        .bingo-cell-mobile {
            min-height: 52px;
            border-radius: 10px;
            background: white;
            border: 2px solid #ddd;
            color: #222;
            font-size: 18px;
            font-weight: 800;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .bingo-cell-marked {
            background: linear-gradient(135deg, #00C853, #64DD17);
            color: white;
            border: 2px solid #00C853;
            text-decoration: line-through;
        }

        @media screen and (max-width: 600px) {
            .bingo-grid {
                grid-template-columns: repeat(5, 1fr);
                gap: 4px;
                width: 100%;
                max-width: 100%;
            }

            .bingo-cell-mobile {
                min-height: 44px;
                font-size: 15px;
                border-radius: 8px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    html = '<div class="bingo-grid">'

    for i in range(5):
        for j in range(5):
            number = board[i][j]

            if marked[i][j]:
                html += f'<div class="bingo-cell-mobile bingo-cell-marked">{number} ✓</div>'
            else:
                html += f'<div class="bingo-cell-mobile">{number}</div>'

    html += '</div>'

    st.markdown(html, unsafe_allow_html=True)

    st.write("")

    if can_click:
        selected_number = st.selectbox(
            "Choose number to call",
            [num for row in board for num in row if num not in st.session_state.called_numbers]
        )

        if st.button("Call Selected Number", use_container_width=True):
            call_number(selected_number)
    else:
        st.info("Wait for your turn to call a number.")


def render_bingo_letters(letters):
    bingo = "BINGO"
    completed_count = len(letters)

    html = '<div class="letter-row">'

    for index, letter in enumerate(bingo):
        if index < completed_count:
            html += f'<div class="letter-done">{letter}</div>'
        else:
            html += f'<div class="letter-pending">{letter}</div>'

    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)


def render_scoreboard():
    if not st.session_state.scoreboard:
        st.info("Scoreboard appears after the game starts")
        return

    for player in st.session_state.scoreboard:
        st.markdown(
            f"""
            <div class="card">
                <h4>{player['name']}</h4>
                <p><b>Completed Lines:</b> {player['lines']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        render_bingo_letters(player["letters"])


if st.session_state.connected:
    st_autorefresh(interval=3000, key="game_refresh")
    auto_receive_updates()


st.markdown(
    """
    <div class="main-title">Multiplayer Bingo</div>
    <div class="subtitle">Create a room, invite friends, and start the match</div>
    """,
    unsafe_allow_html=True
)


if not st.session_state.connected:
    left, mid, right = st.columns([1, 1.5, 1])

    with mid:
        st.markdown(
            """
            <div class="join-card">
                <h2>Create or Join Room</h2>
                <p>Host creates a room. Other players join with the code.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("")

        st.subheader("Create Room")

        if st.button("Create New Room", use_container_width=True):
            code = generate_room_code()
            st.session_state.room_code = code
            st.query_params["room"] = code
            st.rerun()

        if st.session_state.room_code:
            join_link = f"http://localhost:8501/?room={st.session_state.room_code}"

            st.success(f"Room Code: {st.session_state.room_code}")
            st.code(join_link, language="text")

        st.divider()

        st.subheader("Join Room With Code")

        room_code = st.text_input(
            "Enter Room Code",
            value=st.session_state.room_code,
            placeholder="Example: AB12CD"
        ).upper()

        player_name = st.text_input(
            "Enter Player Name",
            placeholder="Example: joanna"
        )

        if st.button("Join Room", use_container_width=True):
            if room_code.strip() == "":
                st.error("Please enter a room code")
            elif player_name.strip() == "":
                st.error("Please enter your name")
            else:
                ws = websocket.WebSocket()
                ws.connect(get_ws_url(room_code))

                ws.send(json.dumps({
                    "event": "join",
                    "player_name": player_name
                }))

                response = wait_for_event(
                    ws,
                    ["your_board", "error", "room_full"]
                )

                if response["event"] == "your_board":
                    st.session_state.ws = ws
                    st.session_state.connected = True
                    st.session_state.player_name = player_name
                    st.session_state.room_code = room_code
                    st.session_state.board = response["board"]
                    st.session_state.marked = response["marked"]

                    update_from_response(response)

                    st.query_params["room"] = room_code
                    st.rerun()
                else:
                    st.error(response["message"])


if st.session_state.connected and not st.session_state.game_started:
    host_name = get_host_name()

    st.subheader(f"Waiting Room: {st.session_state.room_code}")

    st.info("Waiting for players. Minimum 2 players required.")

    st.subheader("Players Joined")

    for player in st.session_state.players:
        if player == st.session_state.player_name and player == host_name:
            st.write(f"✓ {player} (You, Host)")
        elif player == st.session_state.player_name:
            st.write(f"✓ {player} (You)")
        elif player == host_name:
            st.write(f"✓ {player} (Host)")
        else:
            st.write(f"✓ {player}")

    st.write(f"Players: {len(st.session_state.players)} / 4")

    if is_current_user_host():
        if st.button(
            "Start Game",
            use_container_width=True,
            disabled=len(st.session_state.players) < 2
        ):
            send_start_game()
    else:
        st.warning("Waiting for host to start the game.")


if st.session_state.connected and st.session_state.game_started:
    if st.session_state.winner:
        st.markdown(
            f"""
            <div class="winner-box">
                BINGO!<br>
                Winner: {st.session_state.winner}
            </div>
            """,
            unsafe_allow_html=True
        )

        if not st.session_state.celebrated:
            st.balloons()
            st.session_state.celebrated = True

    top1, top2, top3 = st.columns(3)

    with top1:
        st.markdown(
            f"""
            <div class="card">
                <h3>Player</h3>
                <h2>{st.session_state.player_name}</h2>
                <p>Room: {st.session_state.room_code}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with top2:
        st.markdown(
            f"""
            <div class="card">
                <h3>Current Turn</h3>
                <h2>{st.session_state.current_turn}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with top3:
        st.markdown(
            f"""
            <div class="card">
                <h3>Called</h3>
                <h2>{len(st.session_state.called_numbers)} Numbers</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader("Your Bingo Board")

        if st.session_state.winner:
            st.success("Game over!")
        elif st.session_state.current_turn == st.session_state.player_name:
            st.markdown(
                """
                <div class="turn-alert">
                    Your turn! Click a number from your board.
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div class="wait-alert">
                    Please wait for your turn.
                </div>
                """,
                unsafe_allow_html=True
            )

        render_board(st.session_state.board, st.session_state.marked)

    with right_col:
        st.subheader("Called Numbers")

        if st.session_state.called_numbers:
            nums = " ".join(
                [f"`{num}`" for num in st.session_state.called_numbers]
            )
            st.markdown(nums)
        else:
            st.info("No numbers called yet")

        st.divider()

        st.subheader("Scoreboard")
        render_scoreboard()
