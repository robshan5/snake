#!/usr/bin/env python3
"""
Snake — terminal edition
========================
Controls:  Arrow keys or WASD to steer
           P  to pause / unpause
           Q  to quit
           R  to restart (after game over)

Requirements: Python 3.6+  (uses only the standard library)
Run with:     python snake.py
"""

import curses
import random
import time

# ── Layout constants ────────────────────────────────────────────────────────
BOARD_W = 20        # inner play-field width  (logical cells)
BOARD_H = 20        # inner play-field height (rows)
BORDER  = 1         # border thickness
CELL    = 2         # terminal columns per logical cell (makes cells square)
PANEL_W = 18        # right-hand info panel width

# ── Timing ──────────────────────────────────────────────────────────────────
BASE_DELAY  = 0.13   # seconds per tick at speed 1
SPEED_STEP  = 0.007  # delay reduction per 5 points

# ── Directions ──────────────────────────────────────────────────────────────
UP    = (-1,  0)
DOWN  = ( 1,  0)
LEFT  = ( 0, -1)
RIGHT = ( 0,  1)

OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}

# ── Colour pair IDs ─────────────────────────────────────────────────────────
C_BORDER  = 1
C_SNAKE_H = 2   # head
C_SNAKE_B = 3   # body
C_FOOD    = 4
C_SCORE   = 5
C_DEAD    = 6
C_PAUSED  = 7
C_PANEL   = 8


# ────────────────────────────────────────────────────────────────────────────

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_BORDER,  curses.COLOR_CYAN,   -1)
    curses.init_pair(C_SNAKE_H, curses.COLOR_GREEN,  -1)
    curses.init_pair(C_SNAKE_B, curses.COLOR_GREEN,  -1)
    curses.init_pair(C_FOOD,    curses.COLOR_RED,    -1)
    curses.init_pair(C_SCORE,   curses.COLOR_YELLOW, -1)
    curses.init_pair(C_DEAD,    curses.COLOR_RED,    -1)
    curses.init_pair(C_PAUSED,  curses.COLOR_YELLOW, -1)
    curses.init_pair(C_PANEL,   curses.COLOR_WHITE,  -1)


def place_food(snake_set):
    while True:
        r = random.randint(0, BOARD_H - 1)
        c = random.randint(0, BOARD_W - 1)
        if (r, c) not in snake_set:
            return (r, c)


def draw_border(win, top, left):
    """Draw a box around the play-field. Each logical cell is CELL columns wide."""
    attr = curses.color_pair(C_BORDER) | curses.A_BOLD
    h  = BOARD_H + 2 * BORDER
    tw = BOARD_W * CELL + 2 * BORDER   # total terminal width incl. border chars

    # Corners
    win.addch(top,         left,          '╔', attr)
    win.addch(top,         left + tw - 1, '╗', attr)
    try:
        win.addch(top + h - 1, left,          '╚', attr)
    except curses.error:
        pass
    try:
        win.addch(top + h - 1, left + tw - 1, '╝', attr)
    except curses.error:
        pass

    # Top and bottom edges
    for tc in range(1, tw - 1):
        win.addch(top,         left + tc, '═', attr)
        try:
            win.addch(top + h - 1, left + tc, '═', attr)
        except curses.error:
            pass

    # Left and right edges
    for r in range(1, h - 1):
        win.addch(top + r, left,          '║', attr)
        win.addch(top + r, left + tw - 1, '║', attr)


def draw_panel(win, top, left, score, high, speed, length, paused):
    """Right-hand info panel."""
    attr = curses.color_pair(C_PANEL)

    def put(r, text, a=None):
        try:
            win.addstr(top + r, left, text[:PANEL_W], a or attr)
        except curses.error:
            pass

    put(0,  "┌──────────────┐", curses.color_pair(C_BORDER) | curses.A_BOLD)
    put(1,  "│  SNAKE  🐍   │", curses.color_pair(C_BORDER) | curses.A_BOLD)
    put(2,  "└──────────────┘", curses.color_pair(C_BORDER) | curses.A_BOLD)
    put(4,  f"  Score  {score:>5}", curses.color_pair(C_SCORE) | curses.A_BOLD)
    put(5,  f"  Best   {high:>5}", attr)
    put(7,  f"  Length {length:>5}", attr)
    put(8,  f"  Speed  {speed:>5}", attr)
    put(10, "  ────────────  ", attr)
    put(11, "  ↑↓←→ / WASD  ", attr)
    put(12, "  P  pause      ", attr)
    put(13, "  R  restart    ", attr)
    put(14, "  Q  quit       ", attr)

    if paused:
        put(16, "  ⏸  PAUSED    ", curses.color_pair(C_PAUSED) | curses.A_BOLD)


def draw_snake(win, top, left, snake, alive):
    head_attr = curses.color_pair(C_SNAKE_H) | curses.A_BOLD
    body_attr = curses.color_pair(C_SNAKE_B)
    dead_attr = curses.color_pair(C_DEAD)    | curses.A_BOLD

    for i, (r, c) in enumerate(snake):
        sr = top  + BORDER + r
        sc = left + BORDER + c * CELL   # multiply column by CELL
        a  = (head_attr if i == 0 else body_attr) if alive else dead_attr
        ch = ('██' if i == 0 else '▓▓') if alive else '░░'
        try:
            win.addstr(sr, sc, ch, a)
        except curses.error:
            pass


def draw_food(win, top, left, food):
    r, c = food
    sr = top  + BORDER + r
    sc = left + BORDER + c * CELL
    try:
        win.addstr(sr, sc, '◆ ', curses.color_pair(C_FOOD) | curses.A_BOLD)
    except curses.error:
        pass


def overlay_message(win, top, left, lines, attr):
    """Centre a list of strings over the play-field."""
    bh  = BOARD_H + 2 * BORDER
    btw = BOARD_W * CELL + 2 * BORDER   # total terminal width of board area
    start_r = top + bh // 2 - len(lines) // 2
    for i, line in enumerate(lines):
        sc = left + (btw - len(line)) // 2
        try:
            win.addstr(start_r + i, sc, line, attr)
        except curses.error:
            pass


# ────────────────────────────────────────────────────────────────────────────

def game_loop(stdscr):
    init_colors()
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    sh, sw = stdscr.getmaxyx()

    # Terminal width the board occupies: border + CELL cols per cell + border
    board_tw = BOARD_W * CELL + 2 * BORDER

    # Minimum terminal size check
    need_h = BOARD_H + 2 * BORDER + 2
    need_w = board_tw + PANEL_W + 4
    if sh < need_h or sw < need_w:
        stdscr.nodelay(False)
        msg = f"Terminal too small! Need {need_w}x{need_h}, got {sw}x{sh}. Press any key."
        try:
            stdscr.addstr(0, 0, msg[:sw - 1])
        except curses.error:
            pass
        stdscr.getch()
        return

    # Centre the board
    board_top  = (sh - (BOARD_H + 2 * BORDER)) // 2
    board_left = (sw - board_tw - PANEL_W - 2) // 2
    panel_left = board_left + board_tw + 2

    high_score = 0

    while True:   # outer restart loop
        # ── Initial state ────────────────────────────────────────────────
        mid_r = BOARD_H // 2
        mid_c = BOARD_W // 2
        snake      = [(mid_r, mid_c), (mid_r, mid_c - 1), (mid_r, mid_c - 2)]
        snake_set  = set(snake)
        direction  = RIGHT
        next_dir   = RIGHT
        score      = 0
        food       = place_food(snake_set)
        alive      = True
        paused     = False
        last_tick  = time.monotonic()

        while True:   # inner frame loop
            now   = time.monotonic()
            speed = 1 + score // 5
            delay = max(0.05, BASE_DELAY - (speed - 1) * SPEED_STEP)

            # ── Input ────────────────────────────────────────────────────
            key = stdscr.getch()
            curses.flushinp()

            if key in (ord('q'), ord('Q')):
                return

            if key in (ord('r'), ord('R')) and not alive:
                break   # restart

            if key in (ord('p'), ord('P')) and alive:
                paused = not paused

            if not paused and alive:
                if key in (curses.KEY_UP,    ord('w'), ord('W')):
                    nd = UP
                elif key in (curses.KEY_DOWN,  ord('s'), ord('S')):
                    nd = DOWN
                elif key in (curses.KEY_LEFT,  ord('a'), ord('A')):
                    nd = LEFT
                elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
                    nd = RIGHT
                else:
                    nd = next_dir

                if nd != OPPOSITE[direction]:
                    next_dir = nd

            # ── Tick ─────────────────────────────────────────────────────
            if alive and not paused and (now - last_tick) >= delay:
                last_tick = now
                direction = next_dir
                hr, hc = snake[0]
                dr, dc = direction
                nr, nc = hr + dr, hc + dc

                # Wall collision
                if not (0 <= nr < BOARD_H and 0 <= nc < BOARD_W):
                    alive = False
                elif (nr, nc) in snake_set:
                    alive = False
                else:
                    snake.insert(0, (nr, nc))
                    snake_set.add((nr, nc))
                    if (nr, nc) == food:
                        score += 1
                        high_score = max(high_score, score)
                        food = place_food(snake_set)
                    else:
                        tail = snake.pop()
                        snake_set.discard(tail)

            # ── Draw ─────────────────────────────────────────────────────
            stdscr.erase()
            draw_border(stdscr, board_top, board_left)
            draw_snake(stdscr, board_top, board_left, snake, alive)
            draw_food(stdscr, board_top, board_left, food)
            draw_panel(stdscr, board_top, panel_left, score, high_score,
                       speed, len(snake), paused)

            if not alive:
                overlay_message(
                    stdscr, board_top, board_left,
                    ["  GAME OVER  ", f"  Score: {score}  ", "  R restart  Q quit  "],
                    curses.color_pair(C_DEAD) | curses.A_BOLD | curses.A_REVERSE
                )

            stdscr.refresh()
            time.sleep(0.016)   # ~60 fps render cadence


def main():
    try:
        curses.wrapper(game_loop)
    except KeyboardInterrupt:
        pass
    print("Thanks for playing Snake! 🐍")


if __name__ == "__main__":
    main()
