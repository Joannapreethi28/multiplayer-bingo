import os
import json
import time
import socket
import random
import string

import streamlit as st
import websocket
from websocket import (
    WebSocketTimeoutException,
    WebSocketConnectionClosedException,
)
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Multiplayer Bingo",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Backend URL is overridable so the app can be pointed at a local backend
# (e.g. ws://localhost:8000/ws) during development without editing this file.
BACKEND_URL = os.environ.get(
    "BINGO_BACKEND_URL",
    "wss://bingo-backend-2o3a.onrender.com/ws",
)


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
    "celebrated": False,
    "theme": "auto",
    "connection_lost": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


if "room" in st.query_params and st.session_state.room_code == "":
    st.session_state.room_code = st.query_params["room"]


# ---------------------------------------------------------------------------
# Theming
# ---------------------------------------------------------------------------
LIGHT = {
    "--bg": "#eef0f8",
    "--surface": "#ffffff",
    "--surface-2": "#f3f4fb",
    "--text": "#1b1c28",
    "--text-muted": "#697086",
    "--border": "#e2e5f0",
    "--accent": "#6C63FF",
    "--accent-2": "#8E7CFF",
    "--good": "#00b84d",
    "--good-2": "#00C853",
    "--warn-bg": "#fff3e0",
    "--warn-fg": "#b25800",
    "--ok-bg": "#e8f7ed",
    "--ok-fg": "#1b7a37",
    "--shadow": "rgba(31, 41, 89, 0.10)",
}

DARK = {
    "--bg": "#0e1016",
    "--surface": "#191c26",
    "--surface-2": "#222633",
    "--text": "#e9eaf2",
    "--text-muted": "#9aa1b6",
    "--border": "#2c3142",
    "--accent": "#8b84ff",
    "--accent-2": "#a99fff",
    "--good": "#00c95a",
    "--good-2": "#28d96f",
    "--warn-bg": "#3a2a12",
    "--warn-fg": "#ffb766",
    "--ok-bg": "#16301f",
    "--ok-fg": "#6fe69a",
    "--shadow": "rgba(0, 0, 0, 0.45)",
}


def _vars_block(palette):
    lines = "\n".join(f"  {k}: {v};" for k, v in palette.items())
    return ":root{\n" + lines + "\n}"


def theme_palette_css(theme):
    if theme == "light":
        return _vars_block(LIGHT)
    if theme == "dark":
        return _vars_block(DARK)
    # auto: follow the OS / browser preference
    return _vars_block(LIGHT) + "\n@media (prefers-color-scheme: dark){\n" \
        + _vars_block(DARK) + "\n}"


STATIC_CSS = """
.stApp,
[data-testid="stAppViewContainer"] {
    background: var(--bg);
    color: var(--text);
}

[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    max-width: 900px;
    padding-top: 1.4rem;
    padding-bottom: 2rem;
}

h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    color: var(--text);
}

.main-title {
    text-align: center;
    font-size: 44px;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}

.subtitle {
    text-align: center;
    font-size: 17px;
    color: var(--text-muted);
    margin-bottom: 26px;
}

/* Inputs */
[data-testid="stTextInput"] input {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 10px;
}
[data-testid="stTextInput"] input::placeholder {
    color: var(--text-muted);
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    color: #ffffff;
    border: none;
    border-radius: 12px;
    font-weight: 700;
    padding: 0.55rem 1rem;
    transition: transform 0.05s ease, filter 0.15s ease;
}
.stButton > button:hover {
    filter: brightness(1.05);
    color: #ffffff;
}
.stButton > button:active {
    transform: translateY(1px);
}
.stButton > button:disabled {
    background: var(--surface-2);
    color: var(--text-muted);
    filter: none;
}

.card {
    background: var(--surface);
    padding: 18px;
    border-radius: 16px;
    border: 1px solid var(--border);
    box-shadow: 0 4px 14px var(--shadow);
    text-align: center;
    margin-bottom: 12px;
    color: var(--text);
}
.card h2, .card h3, .card h4 { margin: 4px 0; color: var(--text); }
.card p { color: var(--text-muted); margin: 2px 0; }

.join-card {
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    padding: 24px;
    border-radius: 18px;
    color: #ffffff;
    text-align: center;
    box-shadow: 0 8px 24px var(--shadow);
}
.join-card h2 { color: #ffffff; margin: 0 0 6px 0; }
.join-card p { color: rgba(255,255,255,0.9); margin: 0; }

.winner-box {
    background: linear-gradient(135deg, #FFD700, #FFA500);
    padding: 24px;
    border-radius: 20px;
    text-align: center;
    color: #222;
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 18px;
    box-shadow: 0 8px 24px var(--shadow);
}

.turn-alert {
    background: var(--ok-bg);
    color: var(--ok-fg);
    padding: 13px;
    border-radius: 12px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 14px;
}
.wait-alert {
    background: var(--warn-bg);
    color: var(--warn-fg);
    padding: 13px;
    border-radius: 12px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 14px;
}

/* Connection status chip */
.status-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 7px 14px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 14px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
}
.status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}
.dot-on { background: var(--good-2); box-shadow: 0 0 0 4px rgba(0,200,83,0.18); }
.dot-off { background: #e53935; box-shadow: 0 0 0 4px rgba(229,57,53,0.18); }

/* BINGO letters */
.letter-row {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin: 8px 0;
}
.letter-done, .letter-pending {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
}
.letter-done {
    background: var(--good);
    color: #ffffff;
    text-decoration: line-through;
}
.letter-pending {
    background: var(--surface-2);
    color: var(--text-muted);
    border: 1px solid var(--border);
}

/* Called numbers as chips */
.num-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}
.num-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 34px;
    height: 34px;
    padding: 0 8px;
    border-radius: 9px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--text);
    font-weight: 700;
    font-size: 15px;
}

/* Bingo grid built from native Streamlit buttons (no page reload on click).
   Each row is an st.columns(5); we force the 5 columns to stay side by side
   (Streamlit would otherwise let them wrap on narrow screens) and make every
   button a square. */
.st-key-bingoboard [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    gap: 8px !important;
    max-width: 520px;
    margin: 0 auto 8px auto;
}
.st-key-bingoboard [data-testid="stColumn"] {
    min-width: 0 !important;
    width: auto !important;
    flex: 1 1 0 !important;
}
.st-key-bingoboard .stButton,
.st-key-bingoboard .stButton > button {
    width: 100%;
}
.st-key-bingoboard .stButton > button {
    aspect-ratio: 1 / 1;
    min-height: 0;
    border-radius: 12px;
    font-size: 20px;
    font-weight: 800;
    padding: 0;
}
/* clickable cell */
[class*="st-key-b_cell_"] button {
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 2px solid var(--border) !important;
}
[class*="st-key-b_cell_"] button:hover {
    border-color: var(--accent) !important;
    background: var(--surface-2) !important;
}
/* marked cell */
[class*="st-key-b_mark_"] button,
[class*="st-key-b_mark_"] button:disabled {
    background: linear-gradient(135deg, var(--good), var(--good-2)) !important;
    color: #ffffff !important;
    border: none !important;
    opacity: 1 !important;
}
/* disabled / not-your-turn cell */
[class*="st-key-b_dis_"] button,
[class*="st-key-b_dis_"] button:disabled {
    background: var(--surface-2) !important;
    color: var(--text-muted) !important;
    border: 1px solid var(--border) !important;
    opacity: 1 !important;
}

/* Mobile */
@media screen and (max-width: 640px) {
    .block-container {
        padding-left: 0.6rem;
        padding-right: 0.6rem;
        padding-top: 0.8rem;
    }
    .main-title { font-size: 30px; }
    .subtitle { font-size: 14px; margin-bottom: 18px; }
    .st-key-bingoboard [data-testid="stHorizontalBlock"] {
        gap: 5px !important;
        max-width: 100%;
    }
    .st-key-bingoboard .stButton > button {
        font-size: 16px;
        border-radius: 8px;
    }
    .card { padding: 12px; }
    .card h2 { font-size: 19px; }
    .card h3 { font-size: 14px; }
    .winner-box { font-size: 22px; padding: 18px; }
    .num-chip { min-width: 30px; height: 30px; font-size: 14px; }
    .letter-done, .letter-pending { width: 32px; height: 32px; }
}
"""


def inject_theme():
    css = theme_palette_css(st.session_state.theme) + STATIC_CSS
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_sidebar_controls():
    with st.sidebar:
        st.markdown("### 🎯 Bingo")

        options = ["Auto", "Light", "Dark"]
        current = st.session_state.theme.capitalize()
        if current not in options:
            current = "Auto"

        choice = st.radio(
            "Appearance",
            options,
            index=options.index(current),
            horizontal=True,
        )
        st.session_state.theme = choice.lower()


def render_connection_status():
    """Show a live connection chip in the sidebar."""
    if not st.session_state.connected:
        return

    with st.sidebar:
        st.divider()
        if st.session_state.connection_lost:
            st.markdown(
                '<div class="status-chip">'
                '<span class="status-dot dot-off"></span>'
                'Disconnected</div>',
                unsafe_allow_html=True,
            )
            st.caption("Connection to the server was lost. Refresh to rejoin.")
        else:
            st.markdown(
                '<div class="status-chip">'
                '<span class="status-dot dot-on"></span>'
                'Connected</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                f"Room: {st.session_state.room_code} · "
                f"You: {st.session_state.player_name}"
            )


# ---------------------------------------------------------------------------
# Networking helpers
# ---------------------------------------------------------------------------
def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def get_ws_url(room_code):
    return f"{BACKEND_URL}/{room_code}"


def _recv_json(ws, timeout):
    """Receive one JSON message, or None if nothing arrives within `timeout`.

    A read timeout is a normal, expected event (no message waiting) and must NOT
    be treated as a disconnect -- doing so would stop the auto-refresh and freeze
    the game. We only flag the connection as lost on a genuine close.
    """
    try:
        ws.settimeout(timeout)
        raw = ws.recv()
    except (WebSocketTimeoutException, socket.timeout, TimeoutError):
        # Just a read timeout: nothing to read right now. Not a disconnect.
        return None
    except (WebSocketConnectionClosedException, ConnectionResetError,
            BrokenPipeError, ConnectionAbortedError):
        st.session_state.connection_lost = True
        return None
    except OSError:
        # Transient OS-level hiccup; don't kill the session, just try again.
        return None

    if not raw:
        return None

    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def wait_for_event(ws, wanted_events, timeout=12.0):
    """Wait (bounded) for one of `wanted_events`, processing everything seen.

    Returns the matching message, or None on timeout / disconnect. Every message
    received along the way is fed through update_from_response so state stays
    fresh and nothing is silently dropped.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = _recv_json(ws, 0.4)
        if msg is None:
            if st.session_state.connection_lost:
                return None
            continue
        update_from_response(msg)
        if msg.get("event") in wanted_events:
            return msg
    return None


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
        # New round / cleared winner -> allow the win celebration again.
        if response["winner"] is None:
            st.session_state.celebrated = False

    if "boards" in response:
        name = st.session_state.player_name
        if name in response["boards"]:
            st.session_state.board = response["boards"][name]["board"]
            st.session_state.marked = response["boards"][name]["marked"]


def auto_receive_updates():
    if not (st.session_state.connected and st.session_state.ws is not None):
        return

    ws = st.session_state.ws

    # Drain everything that is immediately available, then stop. Each read is
    # time-bounded, so this can never block the session.
    deadline = time.time() + 0.4
    while time.time() < deadline:
        msg = _recv_json(ws, 0.1)
        if msg is None:
            # Either a timeout (nothing pending) or a dropped connection.
            return
        update_from_response(msg)


def get_host_name():
    if st.session_state.players:
        return st.session_state.players[0]
    return None


def is_current_user_host():
    return st.session_state.player_name == get_host_name()


def _send(message, wanted_events):
    """Send a message and wait (bounded) for one of the expected responses.

    If no reply arrives in time we simply return; the 3-second auto-refresh
    will pick up the broadcast state shortly after. We never block forever.
    """
    ws = st.session_state.ws

    try:
        ws.send(json.dumps(message))
    except (WebSocketConnectionClosedException, ConnectionError, OSError):
        st.session_state.connection_lost = True
        st.error("Connection lost. Please refresh to rejoin.")
        return None

    response = wait_for_event(ws, list(wanted_events) + ["error"], timeout=8.0)

    if response is None:
        return None

    if response.get("event") == "error":
        st.error(response.get("message", "Something went wrong"))

    return response


def send_start_game():
    _send(
        {"event": "start_game", "player_name": st.session_state.player_name},
        ["game_started", "error"],
    )
    st.rerun()


def send_restart_game():
    st.session_state.celebrated = False
    _send(
        {"event": "restart_game", "player_name": st.session_state.player_name},
        ["game_restarted", "error"],
    )
    st.rerun()


def call_number(number):
    _send(
        {
            "event": "call_number",
            "player_name": st.session_state.player_name,
            "number": int(number),
        },
        ["number_called", "error"],
    )
    st.rerun()


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_board(board, marked):
    is_my_turn = st.session_state.current_turn == st.session_state.player_name
    game_over = st.session_state.winner is not None

    can_click = (
        is_my_turn
        and not game_over
        and st.session_state.game_started
        and not st.session_state.connection_lost
    )

    # Native buttons (not links) so a click reruns the script instead of
    # reloading the page, which would drop the session and the WebSocket.
    # One st.columns(5) per row keeps a reliable 5x5 layout.
    with st.container(key="bingoboard"):
        for i in range(5):
            cols = st.columns(5, gap="small")
            for j in range(5):
                number = board[i][j]

                with cols[j]:
                    if marked[i][j]:
                        st.button(
                            f"{number} ✓",
                            key=f"b_mark_{i}_{j}",
                            disabled=True,
                            use_container_width=True,
                        )
                    elif can_click:
                        if st.button(
                            f"{number}",
                            key=f"b_cell_{i}_{j}",
                            use_container_width=True,
                        ):
                            if number not in st.session_state.called_numbers:
                                call_number(number)
                    else:
                        st.button(
                            f"{number}",
                            key=f"b_dis_{i}_{j}",
                            disabled=True,
                            use_container_width=True,
                        )


def render_bingo_letters(letters):
    bingo = "BINGO"
    completed_count = len(letters)

    html = '<div class="letter-row">'
    for index, letter in enumerate(bingo):
        css = "letter-done" if index < completed_count else "letter-pending"
        html += f'<div class="{css}">{letter}</div>'
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
            unsafe_allow_html=True,
        )
        render_bingo_letters(player["letters"])


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
render_sidebar_controls()
inject_theme()

if st.session_state.connected and not st.session_state.connection_lost:
    st_autorefresh(interval=3000, key="game_refresh")
    auto_receive_updates()

render_connection_status()


st.markdown(
    """
    <div class="main-title">Multiplayer Bingo</div>
    <div class="subtitle">Create a room, invite friends, and start the match</div>
    """,
    unsafe_allow_html=True,
)


if not st.session_state.connected:
    left, mid, right = st.columns([1, 2, 1])

    with mid:
        st.markdown(
            """
            <div class="join-card">
                <h2>Create or Join Room</h2>
                <p>Host creates a room. Other players join with the code.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        st.subheader("Create Room")

        if st.button("Create New Room", use_container_width=True):
            code = generate_room_code()
            st.session_state.room_code = code
            st.query_params["room"] = code
            st.rerun()

        if st.session_state.room_code:
            join_link = f"?room={st.session_state.room_code}"
            st.success(f"Room Code: {st.session_state.room_code}")
            st.code(join_link, language="text")

        st.divider()
        st.subheader("Join Room With Code")

        room_code = st.text_input(
            "Enter Room Code",
            value=st.session_state.room_code,
            placeholder="Example: AB12CD",
        ).upper()

        player_name = st.text_input(
            "Enter Player Name",
            placeholder="Example: joanna",
        )

        if st.button("Join Room", use_container_width=True):
            if room_code.strip() == "":
                st.error("Please enter a room code")
            elif player_name.strip() == "":
                st.error("Please enter your name")
            else:
                response = None
                try:
                    with st.spinner("Connecting to the server… "
                                    "(a sleeping server can take up to a "
                                    "minute to wake up)"):
                        ws = websocket.create_connection(
                            get_ws_url(room_code), timeout=60
                        )
                        st.session_state.connection_lost = False

                        ws.send(json.dumps({
                            "event": "join",
                            "player_name": player_name,
                        }))

                        response = wait_for_event(
                            ws,
                            ["your_board", "error", "room_full"],
                            timeout=45.0,
                        )
                except (WebSocketConnectionClosedException, ConnectionError,
                        OSError, websocket.WebSocketException) as exc:
                    st.error(f"Could not connect to the server: {exc}")
                    response = None

                if response is None:
                    st.error(
                        "The server didn't respond in time. It may be waking "
                        "up — please try Join again in a few seconds."
                    )
                elif response["event"] == "your_board":
                    st.session_state.ws = ws
                    st.session_state.connected = True
                    st.session_state.connection_lost = False
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
            disabled=len(st.session_state.players) < 2,
        ):
            send_start_game()
    else:
        st.warning("Waiting for host to start the game.")


if st.session_state.connected and st.session_state.game_started:
    if st.session_state.winner:
        st.markdown(
            f"""
            <div class="winner-box">
                🎉 BINGO! 🎉<br>
                Winner: {st.session_state.winner}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state.celebrated:
            st.balloons()
            st.session_state.celebrated = True

        # Play Again / Rematch
        if is_current_user_host():
            if st.button("🔁 Play Again", use_container_width=True):
                send_restart_game()
        else:
            st.info("Waiting for the host to start a new round.")

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
            unsafe_allow_html=True,
        )

    with top2:
        st.markdown(
            f"""
            <div class="card">
                <h3>Current Turn</h3>
                <h2>{st.session_state.current_turn}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with top3:
        st.markdown(
            f"""
            <div class="card">
                <h3>Called</h3>
                <h2>{len(st.session_state.called_numbers)} Numbers</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("Your Bingo Board")

    if st.session_state.winner:
        st.success("Game over!")
    elif st.session_state.connection_lost:
        st.error("Disconnected from the server. Refresh to rejoin.")
    elif st.session_state.current_turn == st.session_state.player_name:
        st.markdown(
            '<div class="turn-alert">Your turn! Tap a number from your board.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="wait-alert">Please wait for your turn.</div>',
            unsafe_allow_html=True,
        )

    if st.session_state.board and st.session_state.marked:
        render_board(st.session_state.board, st.session_state.marked)

    st.divider()
    st.subheader("Called Numbers")

    if st.session_state.called_numbers:
        chips = "".join(
            f'<span class="num-chip">{num}</span>'
            for num in st.session_state.called_numbers
        )
        st.markdown(f'<div class="num-wrap">{chips}</div>',
                    unsafe_allow_html=True)
    else:
        st.info("No numbers called yet")

    st.divider()
    st.subheader("Scoreboard")
    render_scoreboard()

