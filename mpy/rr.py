import time

import micropyxel as pyxel
from simpletouch import SimpleTouch


FPS = 30
SCREEN_W = 32
SCREEN_H = 16
TOUCH_PIN = 38

COL_BLACK = 0
COL_RED = 8
COL_BLOOD_RED = 8
COL_YELLOW = 10
COL_WHITE = 7
COLKEY = COL_BLACK

RR_BANK = 0
RR_ASSET_PATH = "assets/sprites.png"

CHAMBERS = 6
SHOT_FAST_STEP_FRAMES = 3
SHOT_SLOW_STEP_FRAMES = 12
STOP_HOLD_FRAMES = FPS // 2
SPIN_FAST_MIN_FRAMES = FPS * 1
SPIN_FAST_MAX_FRAMES = FPS * 3
SPIN_SLOW_FRAMES = FPS * 3
SHOT_COUNTDOWN_FRAMES = FPS * 3
SHOT_VISIBLE_COUNT = 8
SPIN_FAST_STEPS = 3

STATE_ATTRACT = 0
STATE_LOAD = 1
STATE_ROUND = 2
STATE_SPIN = 3
STATE_STOP = 4
STATE_SHOT = 5

# (src_x, src_y, width, height, dst_x, dst_y), inclusive sprite bounds converted to size.
LOAD_FRAMES = (
    (138, 1, 16, 16, 8, 0),
    (155, 1, 15, 16, 7, 0),
    (171, 1, 15, 16, 5, 0),
    (189, 1, 21, 15, 6, 1),
    (211, 1, 24, 16, 6, 0),
    (140, 55, 24, 16, 6, 0),
    (166, 55, 24, 16, 6, 0),
    (191, 55, 22, 16, 4, 0),
    (214, 55, 16, 16, 6, 0),
    (138, 1, 16, 16, 8, 0),
)

SPIN_FRAMES = (
    (139, 1, 15, 16, 8, 0),
    (155, 18, 15, 16, 8, 0),
    (171, 18, 17, 16, 7, 0),
    (189, 17, 16, 16, 7, 0),
    (211, 18, 17, 16, 7, 0),
    (231, 18, 16, 16, 7, 0),
    (139, 1, 15, 16, 8, 0),
)

LOAD_FRAME_DELAYS = (
    FPS // 5,
    FPS // 5,
    FPS // 5,
    FPS // 5,
    FPS // 2,
    FPS // 2,
    FPS // 2,
    FPS // 5,
    FPS // 5,
    FPS // 5,
)

EMPTY_STOPS = (
    (140, 76, 15, 16, 8, 0),
    (156, 76, 15, 16, 8, 0),
    (174, 76, 15, 16, 8, 0),
    (190, 76, 15, 16, 8, 0),
)

LOADED_STOP = (139, 35, 15, 16, 8, 0)

SHOT_FRAMES = (
    (155, 35, 15, 16, 8, 0),
    (171, 35, 15, 16, 8, 0),
    (189, 35, 15, 16, 8, 0),
    (211, 36, 24, 16, 3, 0),
    (141, 94, 15, 16, 8, 0),
    (157, 94, 30, 16, 2, 0),
    (189, 94, 30, 16, 2, 0),
    (223, 94, 29, 16, 2, 0),
    (106, 19, 32, 16, 0, 0),
    (106, 2, 32, 16, 0, 0),
)


class RussianRouletteApp:
    def __init__(self):
        pyxel.init()
        pyxel.images(RR_BANK).load_from_png(0, 0, RR_ASSET_PATH, True)

        self.touch = SimpleTouch(pin_no=TOUCH_PIN, active_high=True)
        self.rng_state = self._make_seed()

        self.frame = 0
        self.state = STATE_ATTRACT
        self.state_frame = 0
        self.round_no = 1
        self.shot_round = 1
        self.spin_fast_frames = SPIN_FAST_MIN_FRAMES
        self.spin_step = 0
        self.spin_draw_index = 0
        self.stop_sprite = EMPTY_STOPS[0]
        self.round_bg_sprite = LOAD_FRAMES[-1]

    def appUpdate(self, _rt):
        self.frame += 1
        self._update_touch()

        if self.state == STATE_LOAD:
            self._tick_load()
        elif self.state == STATE_SPIN:
            self._tick_spin()
        elif self.state == STATE_STOP:
            self._tick_stop()
        elif self.state == STATE_SHOT:
            self._tick_shot()

    def appDraw(self, _rt):
        pyxel.cls(COL_BLACK)

        if self.state == STATE_ATTRACT:
            self._draw_attract()
        elif self.state == STATE_LOAD:
            self._draw_sprite(LOAD_FRAMES[self._load_index()])
        elif self.state == STATE_ROUND:
            self._draw_round()
        elif self.state == STATE_SPIN:
            self._draw_sprite(SPIN_FRAMES[self.spin_draw_index])
        elif self.state == STATE_STOP:
            self._draw_sprite(self.stop_sprite)
        elif self.state == STATE_SHOT:
            self._draw_shot()

    def appOnExit(self, _rt, reason, exc):
        try:
            pyxel.destroy()
        except Exception:
            pass

    def _update_touch(self):
        self.touch.update()
        while True:
            ev = self.touch.get()
            if ev is None:
                break
            if ev == "double":
                self._set_state(STATE_ATTRACT)
                return
            if ev == "click":
                if self.state == STATE_ATTRACT:
                    self._start_game()
                elif self.state == STATE_ROUND:
                    self._start_trigger()

    def _start_game(self):
        self._mix_rng(self.frame)
        self.round_no = 1
        self.shot_round = self._rand_int(1, CHAMBERS)
        if self.shot_round < 1:
            self.shot_round = 1
        elif self.shot_round > CHAMBERS:
            self.shot_round = CHAMBERS
        self.round_bg_sprite = LOAD_FRAMES[-1]
        self._set_state(STATE_LOAD)

    def _start_trigger(self):
        self._clamp_round()
        self._mix_rng(self.frame + (self.round_no << 8))
        self.spin_fast_frames = self._rand_int(SPIN_FAST_MIN_FRAMES, SPIN_FAST_MAX_FRAMES)
        self.spin_step = 0
        self.spin_draw_index = 0
        if self._is_shot_round():
            self.stop_sprite = LOADED_STOP
        else:
            self.stop_sprite = EMPTY_STOPS[self._rand_int(0, len(EMPTY_STOPS) - 1)]
        self._set_state(STATE_SPIN)

    def _set_state(self, state):
        self.state = state
        self.state_frame = 0

    def _tick_load(self):
        self.state_frame += 1
        if self.state_frame >= self._load_total_frames():
            self.round_bg_sprite = LOAD_FRAMES[-1]
            self._set_state(STATE_ROUND)

    def _tick_spin(self):
        self.state_frame += 1
        self.spin_step += self._spin_steps_this_frame(self.state_frame)
        self.spin_draw_index = self.spin_step % len(SPIN_FRAMES)

        if self.state_frame >= self.spin_fast_frames + SPIN_SLOW_FRAMES:
            self._set_state(STATE_STOP)

    def _tick_stop(self):
        self.state_frame += 1
        if self.state_frame < STOP_HOLD_FRAMES:
            return

        self._clamp_round()
        if self._is_shot_round():
            self._set_state(STATE_SHOT)
        else:
            self.round_no += 1
            self._clamp_round()
            self.round_bg_sprite = self.stop_sprite
            self._set_state(STATE_ROUND)

    def _tick_shot(self):
        self.state_frame += 1
        if self.state_frame >= self._shot_total_frames() + SHOT_COUNTDOWN_FRAMES:
            self._set_state(STATE_ATTRACT)

    def _clamp_round(self):
        if self.round_no < 1:
            self.round_no = 1
        elif self.round_no > CHAMBERS:
            self.round_no = CHAMBERS

    def _is_shot_round(self):
        self._clamp_round()
        return self.round_no >= self.shot_round or self.round_no >= CHAMBERS

    def _spin_steps_this_frame(self, frame_no):
        if frame_no <= self.spin_fast_frames:
            return SPIN_FAST_STEPS

        slow_frame = frame_no - self.spin_fast_frames
        if slow_frame > SPIN_SLOW_FRAMES:
            return 0

        remain = SPIN_SLOW_FRAMES - slow_frame + 1
        if remain <= FPS:
            wait = 8 if remain <= FPS // 3 else 4
            return 1 if (remain == 1 or (frame_no % wait) == 0) else 0
        return 1 + ((SPIN_FAST_STEPS - 1) * remain * remain) // (SPIN_SLOW_FRAMES * SPIN_SLOW_FRAMES)

    def _load_index(self):
        frame = self.state_frame
        for i in range(len(LOAD_FRAME_DELAYS)):
            if frame < LOAD_FRAME_DELAYS[i]:
                return i
            frame -= LOAD_FRAME_DELAYS[i]
        return len(LOAD_FRAMES) - 1

    def _load_total_frames(self):
        total = 0
        for frames in LOAD_FRAME_DELAYS:
            total += frames
        return total

    def _shot_index(self):
        frame = self.state_frame
        for i in range(SHOT_VISIBLE_COUNT):
            step_frames = SHOT_SLOW_STEP_FRAMES if i >= 5 else SHOT_FAST_STEP_FRAMES
            if frame < step_frames:
                return i
            frame -= step_frames
        return SHOT_VISIBLE_COUNT - 1

    def _shot_total_frames(self):
        return SHOT_FAST_STEP_FRAMES * 5 + SHOT_SLOW_STEP_FRAMES * (SHOT_VISIBLE_COUNT - 5)

    def _draw_attract(self):
        self._draw_text_center("Spin", 1, COL_WHITE)

        ring = ((0, -2), (1, -1), (2, 0), (1, 1), (0, 2), (-1, 1), (-2, 0), (-1, -1))
        head = (self.frame // 5) & 7
        cx = SCREEN_W // 2
        cy = 10
        for i in range(4):
            x, y = ring[(head + i) & 7]
            pyxel.pset(cx + x, cy + y, COL_YELLOW)

    def _draw_round(self):
        self._draw_sprite(self.round_bg_sprite)
        self._clamp_round()
        pyxel.text(0, 0, "R%d" % self.round_no, COL_RED)

    def _draw_shot(self):
        total = self._shot_total_frames()
        if self.state_frame < total:
            self._draw_sprite(SHOT_FRAMES[self._shot_index()])
            return

        count = 3 - ((self.state_frame - total) // FPS)
        if count < 1:
            count = 1
        shake = ((0, 0), (1, 0), (0, 0), (-1, 0), (0, 0), (0, 0))[self.state_frame % 6]
        self._draw_big_digit(count, 12 + shake[0], 3, COL_BLOOD_RED)

    def _draw_big_digit(self, digit, x, y, color):
        patterns = (
            ("010", "110", "010", "010", "111"),
            ("111", "001", "111", "100", "111"),
            ("111", "001", "111", "001", "111"),
        )
        rows = patterns[digit - 1]
        for row in range(5):
            line = rows[row]
            for col in range(3):
                if line[col] == "1":
                    pyxel.rect(x + col * 3, y + row * 3, 2, 2, color)

    def _draw_sprite(self, sprite):
        self._draw_sprite_offset(sprite, 0, 0)

    def _draw_sprite_offset(self, sprite, ox, oy):
        src_x, src_y, w, h, dst_x, dst_y = sprite
        pyxel.blt(dst_x + ox, dst_y + oy, RR_BANK, src_x, src_y, w, h, COLKEY)

    def _draw_text_center(self, text, y, color):
        x = (SCREEN_W - len(text) * 4) // 2
        if x < 0:
            x = 0
        pyxel.text(x, y, text, color)

    def _make_seed(self):
        seed = 0x9E3779B9
        try:
            seed ^= time.ticks_ms()
        except Exception:
            pass
        try:
            seed ^= time.ticks_us() << 7
        except Exception:
            pass
        return seed & 0xFFFFFFFF or 1

    def _mix_rng(self, value):
        self.rng_state ^= value & 0xFFFFFFFF
        self.rng_state ^= (self.rng_state << 13) & 0xFFFFFFFF
        self.rng_state ^= self.rng_state >> 17
        self.rng_state ^= (self.rng_state << 5) & 0xFFFFFFFF
        self.rng_state &= 0xFFFFFFFF
        if self.rng_state == 0:
            self.rng_state = 1

    def _rand_u32(self):
        self._mix_rng(0xA5A5A5A5)
        return self.rng_state

    def _rand_int(self, lo, hi):
        if hi <= lo:
            return lo
        span = hi - lo + 1
        return lo + (self._rand_u32() % span)


def appMain():
    app = RussianRouletteApp()
    pyxel.run(app.appUpdate, app.appDraw, fps=FPS, on_exit=app.appOnExit)


if __name__ == "__main__":
    appMain()
