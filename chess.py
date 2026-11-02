#!/usr/bin/env python3
# yo this is totally not vibe coded by claude sonnet 5 at medium
"""
Terminal Chess vs Bot — WASD + Spacebar controls (single-file version)
Run with: python3 chess_wasd.py

Controls:
  W A S D   move the highlighted cursor around the board
  SPACE     select a piece / confirm a move to the highlighted square
  SPACE again on the same square   deselects it
  Q         quit (with confirmation)

Move a pawn to the last rank and you'll be asked to pick Q/R/B/N to promote.
"""

import curses
import time
import random

# ---------------------------------------------------------------- constants

PIECE_VALUES = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}

PAWN_PST = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [5, 10, 10, -20, -20, 10, 10, 5],
    [5, -5, -10, 0, 0, -10, -5, 5],
    [0, 0, 0, 20, 20, 0, 0, 0],
    [5, 5, 10, 25, 25, 10, 5, 5],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

KNIGHT_PST = [
    [-50, -40, -30, -30, -30, -30, -40, -50],
    [-40, -20, 0, 5, 5, 0, -20, -40],
    [-30, 5, 10, 15, 15, 10, 5, -30],
    [-30, 0, 15, 20, 20, 15, 0, -30],
    [-30, 5, 15, 20, 20, 15, 5, -30],
    [-30, 0, 10, 15, 15, 10, 0, -30],
    [-40, -20, 0, 0, 0, 0, -20, -40],
    [-50, -40, -30, -30, -30, -30, -40, -50],
]

BISHOP_DIRS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ROOK_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
QUEEN_DIRS = BISHOP_DIRS + ROOK_DIRS
KNIGHT_OFFSETS = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]

UNICODE_PIECES = {
    "K": "\u2654", "Q": "\u2655", "R": "\u2656", "B": "\u2657", "N": "\u2658", "P": "\u2659",
    "k": "\u265A", "q": "\u265B", "r": "\u265C", "b": "\u265D", "n": "\u265E", "p": "\u265F",
}

# ---------------------------------------------------------------- helpers


def in_bounds(r, c):
    return 0 <= r < 8 and 0 <= c < 8


def piece_color(p):
    if p == ".":
        return None
    return "w" if p.isupper() else "b"


def square_name(r, c):
    return f"{chr(ord('a') + c)}{r + 1}"


def initial_state():
    board = [["." for _ in range(8)] for _ in range(8)]
    back = ["R", "N", "B", "Q", "K", "B", "N", "R"]
    for c in range(8):
        board[0][c] = back[c]
        board[1][c] = "P"
        board[6][c] = "p"
        board[7][c] = back[c].lower()
    return {
        "board": board,
        "turn": "w",
        "castling": {"K": True, "Q": True, "k": True, "q": True},
        "en_passant": None,
        "halfmove": 0,
        "fullmove": 1,
    }


# ---------------------------------------------------------------- attacks


def square_attacked(board, row, col, by_color):
    # pawns
    if by_color == "w":
        for dc in (-1, 1):
            r, c = row - 1, col + dc
            if in_bounds(r, c) and board[r][c] == "P":
                return True
    else:
        for dc in (-1, 1):
            r, c = row + 1, col + dc
            if in_bounds(r, c) and board[r][c] == "p":
                return True
    # knights
    for dr, dc in KNIGHT_OFFSETS:
        r, c = row + dr, col + dc
        if in_bounds(r, c):
            p = board[r][c]
            if p != "." and p.upper() == "N" and piece_color(p) == by_color:
                return True
    # king
    for dr, dc in QUEEN_DIRS:
        r, c = row + dr, col + dc
        if in_bounds(r, c):
            p = board[r][c]
            if p != "." and p.upper() == "K" and piece_color(p) == by_color:
                return True
    # sliding diagonal (bishop/queen)
    for dr, dc in BISHOP_DIRS:
        r, c = row + dr, col + dc
        while in_bounds(r, c):
            p = board[r][c]
            if p != ".":
                if piece_color(p) == by_color and p.upper() in ("B", "Q"):
                    return True
                break
            r += dr
            c += dc
    # sliding orthogonal (rook/queen)
    for dr, dc in ROOK_DIRS:
        r, c = row + dr, col + dc
        while in_bounds(r, c):
            p = board[r][c]
            if p != ".":
                if piece_color(p) == by_color and p.upper() in ("R", "Q"):
                    return True
                break
            r += dr
            c += dc
    return False


def find_king(board, color):
    target = "K" if color == "w" else "k"
    for r in range(8):
        for c in range(8):
            if board[r][c] == target:
                return r, c
    return None


def in_check(state, color):
    board = state["board"]
    kr_kc = find_king(board, color)
    if kr_kc is None:
        return False
    kr, kc = kr_kc
    enemy = "b" if color == "w" else "w"
    return square_attacked(board, kr, kc, enemy)


# ---------------------------------------------------------------- move generation


def pawn_moves(state, r, c, color):
    board = state["board"]
    moves = []
    direction = 1 if color == "w" else -1
    start_row = 1 if color == "w" else 6
    promo_row = 7 if color == "w" else 0

    r1 = r + direction
    if in_bounds(r1, c) and board[r1][c] == ".":
        if r1 == promo_row:
            for promo in ("Q", "R", "B", "N"):
                moves.append((r, c, r1, c, promo, "normal"))
        else:
            moves.append((r, c, r1, c, None, "normal"))
            if r == start_row:
                r2 = r + 2 * direction
                if board[r2][c] == ".":
                    moves.append((r, c, r2, c, None, "double_pawn"))

    for dc in (-1, 1):
        c1 = c + dc
        if not in_bounds(r1, c1):
            continue
        target = board[r1][c1]
        if target != "." and piece_color(target) != color:
            if r1 == promo_row:
                for promo in ("Q", "R", "B", "N"):
                    moves.append((r, c, r1, c1, promo, "normal"))
            else:
                moves.append((r, c, r1, c1, None, "normal"))
        elif state["en_passant"] == (r1, c1):
            moves.append((r, c, r1, c1, None, "enpassant"))
    return moves


def knight_moves(state, r, c, color):
    board = state["board"]
    moves = []
    for dr, dc in KNIGHT_OFFSETS:
        nr, nc = r + dr, c + dc
        if in_bounds(nr, nc):
            target = board[nr][nc]
            if target == "." or piece_color(target) != color:
                moves.append((r, c, nr, nc, None, "normal"))
    return moves


def sliding_moves(state, r, c, color, dirs):
    board = state["board"]
    moves = []
    for dr, dc in dirs:
        nr, nc = r + dr, c + dc
        while in_bounds(nr, nc):
            target = board[nr][nc]
            if target == ".":
                moves.append((r, c, nr, nc, None, "normal"))
            else:
                if piece_color(target) != color:
                    moves.append((r, c, nr, nc, None, "normal"))
                break
            nr += dr
            nc += dc
    return moves


def king_moves(state, r, c, color):
    board = state["board"]
    moves = []
    for dr, dc in QUEEN_DIRS:
        nr, nc = r + dr, c + dc
        if in_bounds(nr, nc):
            target = board[nr][nc]
            if target == "." or piece_color(target) != color:
                moves.append((r, c, nr, nc, None, "normal"))

    enemy = "b" if color == "w" else "w"
    home_row = 0 if color == "w" else 7
    if r == home_row and c == 4 and not square_attacked(board, r, c, enemy):
        rights = state["castling"]
        king_side = "K" if color == "w" else "k"
        queen_side = "Q" if color == "w" else "q"
        if (
            rights.get(king_side)
            and board[home_row][5] == "."
            and board[home_row][6] == "."
            and board[home_row][7] == ("R" if color == "w" else "r")
            and not square_attacked(board, home_row, 5, enemy)
            and not square_attacked(board, home_row, 6, enemy)
        ):
            moves.append((r, c, home_row, 6, None, "castle_k"))
        if (
            rights.get(queen_side)
            and board[home_row][1] == "."
            and board[home_row][2] == "."
            and board[home_row][3] == "."
            and board[home_row][0] == ("R" if color == "w" else "r")
            and not square_attacked(board, home_row, 3, enemy)
            and not square_attacked(board, home_row, 2, enemy)
        ):
            moves.append((r, c, home_row, 2, None, "castle_q"))
    return moves


def generate_pseudo_legal_moves(state, color):
    board = state["board"]
    moves = []
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p == "." or piece_color(p) != color:
                continue
            pt = p.upper()
            if pt == "P":
                moves.extend(pawn_moves(state, r, c, color))
            elif pt == "N":
                moves.extend(knight_moves(state, r, c, color))
            elif pt == "B":
                moves.extend(sliding_moves(state, r, c, color, BISHOP_DIRS))
            elif pt == "R":
                moves.extend(sliding_moves(state, r, c, color, ROOK_DIRS))
            elif pt == "Q":
                moves.extend(sliding_moves(state, r, c, color, QUEEN_DIRS))
            elif pt == "K":
                moves.extend(king_moves(state, r, c, color))
    return moves


def apply_move(state, move):
    fr, fc, tr, tc, promo, flag = move
    board = [row[:] for row in state["board"]]
    castling = dict(state["castling"])
    en_passant = None

    piece = board[fr][fc]
    color = piece_color(piece)
    captured = board[tr][tc]

    if flag == "enpassant":
        board[fr][tc] = "."  # remove the captured pawn
        captured = "p" if color == "w" else "P"

    board[tr][tc] = piece
    board[fr][fc] = "."

    if promo:
        board[tr][tc] = promo if color == "w" else promo.lower()

    if flag == "castle_k":
        board[fr][5] = board[fr][7]
        board[fr][7] = "."
    elif flag == "castle_q":
        board[fr][3] = board[fr][0]
        board[fr][0] = "."

    if flag == "double_pawn":
        en_passant = ((fr + tr) // 2, fc)

    if piece == "K":
        castling["K"] = False
        castling["Q"] = False
    if piece == "k":
        castling["k"] = False
        castling["q"] = False
    for sq, key in (((0, 0), "Q"), ((0, 7), "K"), ((7, 0), "q"), ((7, 7), "k")):
        if (fr, fc) == sq or (tr, tc) == sq:
            castling[key] = False

    reset_halfmove = piece.upper() == "P" or captured != "."
    return {
        "board": board,
        "turn": "b" if color == "w" else "w",
        "castling": castling,
        "en_passant": en_passant,
        "halfmove": 0 if reset_halfmove else state["halfmove"] + 1,
        "fullmove": state["fullmove"] + (1 if color == "b" else 0),
    }


def is_legal(state, move):
    new_state = apply_move(state, move)
    color = state["turn"]
    kr_kc = find_king(new_state["board"], color)
    if kr_kc is None:
        return False
    kr, kc = kr_kc
    enemy = "b" if color == "w" else "w"
    return not square_attacked(new_state["board"], kr, kc, enemy)


def legal_moves(state):
    color = state["turn"]
    pseudo = generate_pseudo_legal_moves(state, color)
    return [m for m in pseudo if is_legal(state, m)]


# ---------------------------------------------------------------- evaluation / bot


def eval_board(board):
    score = 0
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p == ".":
                continue
            value = PIECE_VALUES[p.upper()]
            if p.upper() == "P":
                bonus = PAWN_PST[r][c] if p.isupper() else PAWN_PST[7 - r][c]
            elif p.upper() == "N":
                bonus = KNIGHT_PST[r][c] if p.isupper() else KNIGHT_PST[7 - r][c]
            else:
                center_dist = abs(3.5 - r) + abs(3.5 - c)
                bonus = int((7 - center_dist) * 2)
            score += (value + bonus) if p.isupper() else -(value + bonus)
    return score


def negamax(state, depth, alpha, beta):
    moves = legal_moves(state)
    if not moves:
        if in_check(state, state["turn"]):
            return -999999
        return 0
    if depth == 0:
        val = eval_board(state["board"])
        return val if state["turn"] == "w" else -val

    best = -float("inf")
    for m in moves:
        new_state = apply_move(state, m)
        score = -negamax(new_state, depth - 1, -beta, -alpha)
        if score > best:
            best = score
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    return best


def get_best_move(state, depth):
    moves = legal_moves(state)
    if not moves:
        return None, 0
    random.shuffle(moves)
    alpha, beta = -float("inf"), float("inf")
    best_move, best_score = moves[0], -float("inf")
    for m in moves:
        new_state = apply_move(state, m)
        score = -negamax(new_state, depth - 1, -beta, -alpha)
        if score > best_score:
            best_score, best_move = score, m
        if best_score > alpha:
            alpha = best_score
    return best_move, best_score


def bot_move(state, level):
    moves = legal_moves(state)
    if not moves:
        return None
    if level == 1:
        if random.random() < 0.85:
            return random.choice(moves)
        mv, _ = get_best_move(state, 1)
        return mv
    elif level == 2:
        if random.random() < 0.20:
            return random.choice(moves)
        mv, _ = get_best_move(state, 2)
        return mv
    else:
        if random.random() < 0.05:
            return random.choice(moves)
        mv, _ = get_best_move(state, 3)
        return mv


# ---------------------------------------------------------------- display / input


def print_board(board, flip=False):
    files = "abcdefgh"
    rows = range(7, -1, -1) if not flip else range(0, 8)
    cols = range(8) if not flip else range(7, -1, -1)
    header = "  " + " ".join(files[c] for c in cols)
    print(header)
    for r in rows:
        row_cells = []
        for c in cols:
            p = board[r][c]
            row_cells.append(UNICODE_PIECES[p] if p != "." else ".")
        print(f"{r + 1} " + " ".join(row_cells) + f" {r + 1}")
    print(header)


def parse_move(state, user_input):
    user_input = user_input.strip().lower()
    if len(user_input) not in (4, 5):
        return None
    try:
        fc = ord(user_input[0]) - ord("a")
        fr = int(user_input[1]) - 1
        tc = ord(user_input[2]) - ord("a")
        tr = int(user_input[3]) - 1
    except (ValueError, IndexError):
        return None
    if not (in_bounds(fr, fc) and in_bounds(tr, tc)):
        return None

    promo = user_input[4].upper() if len(user_input) == 5 else None
    candidates = [m for m in legal_moves(state) if m[0] == fr and m[1] == fc and m[2] == tr and m[3] == tc]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    for m in candidates:
        if m[4] == promo:
            return m
    for m in candidates:
        if m[4] == "Q":
            return m
    return candidates[0]


# ---------------------------------------------------------------- main loop



# ---------------------------------------------------------------- pure logic
# (kept separate from curses so it can be unit-tested without a real terminal)


def moves_from_square(state, r, c):
    return [m for m in legal_moves(state) if m[0] == r and m[1] == c]


def target_squares(moves):
    return sorted({(m[2], m[3]) for m in moves})


def moves_between(state, fr, fc, tr, tc):
    return [m for m in legal_moves(state) if (m[0], m[1], m[2], m[3]) == (fr, fc, tr, tc)]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def move_cursor(row, col, key, flip):
    if not flip:
        deltas = {"w": (1, 0), "s": (-1, 0), "a": (0, -1), "d": (0, 1)}
    else:
        deltas = {"w": (-1, 0), "s": (1, 0), "a": (0, 1), "d": (0, -1)}
    dr, dc = deltas.get(key, (0, 0))
    return clamp(row + dr, 0, 7), clamp(col + dc, 0, 7)


# ---------------------------------------------------------------- curses UI

COLOR_LIGHT = 1
COLOR_DARK = 2
COLOR_CURSOR = 3
COLOR_SELECTED = 4
COLOR_TARGET = 5
COLOR_CHECK = 6


def init_colors():
    curses.start_color()
    curses.init_pair(COLOR_LIGHT, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(COLOR_DARK, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(COLOR_CURSOR, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(COLOR_SELECTED, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(COLOR_TARGET, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(COLOR_CHECK, curses.COLOR_WHITE, curses.COLOR_RED)


def board_rows_cols(flip):
    rows = range(7, -1, -1) if not flip else range(0, 8)
    cols = range(0, 8) if not flip else range(7, -1, -1)
    return list(rows), list(cols)


def draw(win, state, cursor, selected, targets, flip, status_lines):
    win.erase()
    rows, cols = board_rows_cols(flip)
    files = "abcdefgh"

    check_sq = None
    if in_check(state, state["turn"]):
        check_sq = find_king(state["board"], state["turn"])

    top, left = 1, 4
    header = "   " + "".join(f" {files[c]} " for c in cols)
    win.addstr(top, left - 2, header)

    for i, r in enumerate(rows):
        y = top + 1 + i
        win.addstr(y, left - 3, f"{r + 1:2} ")
        x = left
        for c in cols:
            piece = state["board"][r][c]
            glyph = UNICODE_PIECES[piece] if piece != "." else "."
            is_light = (r + c) % 2 == 1
            pair = COLOR_LIGHT if is_light else COLOR_DARK

            if check_sq == (r, c):
                pair = COLOR_CHECK
            if (r, c) in targets:
                pair = COLOR_TARGET
            if selected == (r, c):
                pair = COLOR_SELECTED
            if cursor == (r, c):
                pair = COLOR_CURSOR

            try:
                win.addstr(y, x, f" {glyph} ", curses.color_pair(pair))
            except curses.error:
                pass
            x += 3
        win.addstr(y, x, f" {r + 1}")

    win.addstr(top + 10, left - 2, header)

    status_y = top + 12
    for line in status_lines:
        try:
            win.addstr(status_y, 2, line)
        except curses.error:
            pass
        status_y += 1

    win.refresh()


def ask_promotion(win, status_row):
    win.addstr(status_row, 2, "Promote to:  (q)ueen  (r)ook  (b)ishop  (n)knight     ")
    win.refresh()
    win.nodelay(False)
    while True:
        key = win.getch()
        ch = chr(key).lower() if 0 <= key < 256 else ""
        if ch in ("q", "r", "b", "n"):
            return ch.upper()


def confirm_quit(win, status_row):
    win.addstr(status_row, 2, "Quit game? (y/n)                                       ")
    win.refresh()
    while True:
        key = win.getch()
        ch = chr(key).lower() if 0 <= key < 256 else ""
        if ch == "y":
            return True
        if ch == "n":
            return False


def play(stdscr, player_color, level):
    curses.curs_set(0)
    init_colors()
    stdscr.keypad(1)

    state = initial_state()
    flip = player_color == "b"
    cursor = (1, 4) if player_color == "w" else (6, 4)
    selected = None
    targets = []
    last_move_text = "—"
    message = "Select a piece with SPACE."

    while True:
        color = state["turn"]
        moves = legal_moves(state)

        if not moves or state["halfmove"] >= 100:
            if not moves and in_check(state, color):
                winner = "Black" if color == "w" else "White"
                message = f"Checkmate! {winner} wins. Press any key to exit."
            elif not moves:
                message = "Stalemate — draw. Press any key to exit."
            else:
                message = "Draw by 50-move rule. Press any key to exit."
            status = [
                f"Bot level: {level}    Last move: {last_move_text}",
                message,
            ]
            draw(stdscr, state, cursor, selected, targets, flip, status)
            stdscr.getch()
            return

        in_chk = in_check(state, color)
        turn_name = "White" if color == "w" else "Black"
        status = [
            f"Bot level: {level}    Last move: {last_move_text}",
            f"Turn: {turn_name}" + ("  (CHECK!)" if in_chk else ""),
            message,
            "WASD: move cursor   SPACE: select/move   Q: quit",
        ]

        if color != player_color:
            draw(stdscr, state, cursor, selected, targets, flip, status[:1] + [f"Turn: {turn_name}", "Bot is thinking...", status[3]])
            time.sleep(0.3)
            mv = bot_move(state, level)
            state = apply_move(state, mv)
            last_move_text = square_name(mv[0], mv[1]) + square_name(mv[2], mv[3])
            message = f"Bot played {last_move_text}. Your move."
            selected = None
            targets = []
            continue

        draw(stdscr, state, cursor, selected, targets, flip, status)
        key = stdscr.getch()
        ch = chr(key).lower() if 0 <= key < 256 else ""

        if ch in ("w", "a", "s", "d"):
            cursor = move_cursor(cursor[0], cursor[1], ch, flip)
            continue

        if ch == "q":
            if confirm_quit(stdscr, 15):
                return
            continue

        if key == ord(" "):
            r, c = cursor
            piece = state["board"][r][c]

            if selected is None:
                if piece != "." and piece_color(piece) == player_color:
                    cand = moves_from_square(state, r, c)
                    if not cand:
                        message = "That piece has no legal moves."
                    else:
                        selected = (r, c)
                        targets = target_squares(cand)
                        message = f"Selected {square_name(r, c)}. Choose a destination."
                else:
                    message = "Select one of your own pieces first."
            else:
                if (r, c) == selected:
                    selected = None
                    targets = []
                    message = "Deselected."
                elif piece != "." and piece_color(piece) == player_color:
                    cand = moves_from_square(state, r, c)
                    if not cand:
                        message = "That piece has no legal moves."
                        selected = None
                        targets = []
                    else:
                        selected = (r, c)
                        targets = target_squares(cand)
                        message = f"Selected {square_name(r, c)}. Choose a destination."
                elif (r, c) in targets:
                    cands = moves_between(state, selected[0], selected[1], r, c)
                    if len(cands) > 1:
                        promo = ask_promotion(stdscr, 15)
                        mv = next(m for m in cands if m[4] == promo)
                    else:
                        mv = cands[0]
                    move_text = square_name(mv[0], mv[1]) + square_name(mv[2], mv[3])
                    state = apply_move(state, mv)
                    last_move_text = move_text
                    message = f"You played {move_text}."
                    selected = None
                    targets = []
                else:
                    message = "Not a legal move for the selected piece."


def main():
    print("=== Python Terminal Chess (WASD + Space) ===\n")
    side = input("Play as White or Black? (w/b): ").strip().lower()
    player_color = "b" if side.startswith("b") else "w"

    print("\nChoose bot difficulty:")
    print(" 1) ~100 elo  (very easy)")
    print(" 2) ~500 elo  (medium)")
    print(" 3) ~1000 elo (hardest)")
    lvl = input("Enter 1, 2, or 3: ").strip()
    level = int(lvl) if lvl in ("1", "2", "3") else 1

    print("\nStarting... WASD to move the cursor, SPACE to select/move, Q to quit.\n")
    time.sleep(1)

    curses.wrapper(play, player_color, level)
    print("Thanks for playing!")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGame interrupted. Bye!")
