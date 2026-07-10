import time

import micropyxel as pyxel
import mpy_button as touch_events


FPS = 30
SCREEN_W = 32
SCREEN_H = 16

COL_BLACK = 0
COLKEY = COL_BLACK

RPS_BANK = 0
RPS_ASSET_PATH = "assets/sprites.png"
RPS_SRC_X = 0
RPS_W = 23
RPS_COUNT = 3

PAPER = 0
SCISSORS = 1
ROCK = 2

RPS_SRC_Y = (0, 16, 31)
RPS_H = (16, 15, 14)
RPS_X = (SCREEN_W - RPS_W) // 2
RPS_BOTTOM_Y = SCREEN_H - 1

STEP_FAST_FRAMES = FPS // 5
STEP_SLOW_FRAMES = FPS
ROLL_MIN_LOOPS = 2
ROLL_MAX_LOOPS = 3

STATE_IDLE = 0
STATE_ROLLING = 1
STATE_DONE = 2


class RpsApp:
    def __init__(self, touch_enabled=True):
        pyxel.init()
        pyxel.images(RPS_BANK).load_from_png(0, 0, RPS_ASSET_PATH, True)

        self.touch = touch_events if touch_enabled else None
        if self.touch is not None:
            self.touch.clear()
        self.rng_state = self._make_seed()

        self.frame = 0
        self.roll_frame = 0
        self.next_step_frame = STEP_FAST_FRAMES
        self.start_item = PAPER
        self.current_item = PAPER
        self.target_item = PAPER
        self.total_steps = 0
        self.steps_done = 0
        self.state = STATE_IDLE

    def start_roll(self):
        self._mix_rng(self.frame + (self.current_item << 8) + self.roll_frame)

        self.state = STATE_ROLLING
        self.roll_frame = 0
        self.steps_done = 0

        self.start_item = self.current_item
        self.target_item = self._rand_int(0, RPS_COUNT - 1)
        loops = self._rand_int(ROLL_MIN_LOOPS, ROLL_MAX_LOOPS)
        advance = (self.target_item - self.start_item) % RPS_COUNT
        self.total_steps = loops * RPS_COUNT + advance
        self.next_step_frame = self._step_due_frame(1)

    def appUpdate(self, _rt):
        self.frame += 1
        self._update_touch()

        if self.state == STATE_ROLLING:
            self._update_roll()

    def appDraw(self, _rt):
        pyxel.cls(COL_BLACK)
        self._draw_item()

    def appOnExit(self, _rt, reason, exc):
        try:
            pyxel.destroy()
        except Exception:
            pass

    def _update_touch(self):
        if self.touch is None:
            return
        while True:
            ev = self.touch.get()
            if ev is None:
                break
            self.handle_touch_event(ev)

    def handle_touch_event(self, ev):
        if ev == "click" or ev == "double":
            if self.state != STATE_ROLLING:
                self.start_roll()

    def _update_roll(self):
        self.roll_frame += 1

        if self.roll_frame < self.next_step_frame:
            return

        self.steps_done += 1
        self.current_item = (self.start_item + self.steps_done) % RPS_COUNT

        if self.steps_done >= self.total_steps:
            self.current_item = self.target_item
            self.state = STATE_DONE
            return

        self.next_step_frame += self._step_interval(self.steps_done + 1)

    def _step_due_frame(self, step_no):
        due = 0
        for i in range(1, step_no + 1):
            due += self._step_interval(i)
        return due

    def _step_interval(self, step_no):
        if self.total_steps <= 1:
            return STEP_SLOW_FRAMES

        t = ((step_no - 1) * 1024) // (self.total_steps - 1)
        return STEP_FAST_FRAMES + (((STEP_SLOW_FRAMES - STEP_FAST_FRAMES) * t * t) // (1024 * 1024))

    def _draw_item(self):
        item = self.current_item
        h = RPS_H[item]
        y = RPS_BOTTOM_Y - h + 1
        pyxel.blt(RPS_X, y, RPS_BANK, RPS_SRC_X, RPS_SRC_Y[item], RPS_W, h, COLKEY)

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
    app = RpsApp()
    pyxel.run(app.appUpdate, app.appDraw, fps=FPS, on_exit=app.appOnExit)


if __name__ == "__main__":
    appMain()
