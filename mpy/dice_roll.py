import time

import micropyxel as pyxel
from simpletouch import SimpleTouch


FPS = 30
SCREEN_W = 32
SCREEN_H = 16
TOUCH_PIN = 38

COL_BLACK = 0
COLKEY = COL_BLACK

DICE_BANK = 0
DICE_ASSET_PATH = "assets/sprites.png"
DICE_SRC_X = 40
DICE_SRC_Y = 121
DICE_W = 16
DICE_H = 15
DICE_COUNT = 6
DICE_X = (SCREEN_W - DICE_W) // 2
DICE_Y = (SCREEN_H - DICE_H) // 2

ROLL_BASE_FRAMES = FPS * 2
ROLL_EXTRA_FRAMES = FPS // 2
ROLL_MIN_LOOPS = 7
ROLL_MAX_LOOPS = 11

STATE_IDLE = 0
STATE_ROLLING = 1
STATE_DONE = 2


class DiceRollApp:
    def __init__(self):
        pyxel.init()
        pyxel.images(DICE_BANK).load_from_png(0, 0, DICE_ASSET_PATH, True)

        self.touch = SimpleTouch(pin_no=TOUCH_PIN, active_high=True)
        self.rng_state = self._make_seed()

        self.frame = 0
        self.roll_frame = 0
        self.roll_total = ROLL_BASE_FRAMES
        self.start_face = 0
        self.current_face = 0
        self.target_face = 0
        self.total_steps = 0
        self.state = STATE_IDLE

    def start_roll(self):
        self._mix_rng(self.frame + (self.current_face << 8) + self.roll_frame)

        self.state = STATE_ROLLING
        self.roll_frame = 0
        self.roll_total = ROLL_BASE_FRAMES + self._rand_int(0, ROLL_EXTRA_FRAMES)

        self.start_face = self.current_face
        self.target_face = self._rand_int(0, DICE_COUNT - 1)
        loops = self._rand_int(ROLL_MIN_LOOPS, ROLL_MAX_LOOPS)
        advance = (self.target_face - self.start_face) % DICE_COUNT
        self.total_steps = loops * DICE_COUNT + advance

    def appUpdate(self, _rt):
        self.frame += 1
        self._update_touch()

        if self.state == STATE_ROLLING:
            self._update_roll()

    def appDraw(self, _rt):
        pyxel.cls(COL_BLACK)
        self._draw_dice()

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
            if ev == "click" or ev == "double":
                if self.state != STATE_ROLLING:
                    self.start_roll()

    def _update_roll(self):
        self.roll_frame += 1

        if self.roll_frame >= self.roll_total:
            self.current_face = self.target_face
            self.state = STATE_DONE
            return

        t = (self.roll_frame * 1024) // self.roll_total
        inv = 1024 - t
        eased = 1024 - ((inv * inv * inv) // (1024 * 1024))
        step = (self.total_steps * eased) // 1024
        self.current_face = (self.start_face + step) % DICE_COUNT

    def _draw_dice(self):
        src_x = DICE_SRC_X + self.current_face * DICE_W
        pyxel.blt(DICE_X, DICE_Y, DICE_BANK, src_x, DICE_SRC_Y, DICE_W, DICE_H, COLKEY)

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
    app = DiceRollApp()
    pyxel.run(app.appUpdate, app.appDraw, fps=FPS, on_exit=app.appOnExit)


if __name__ == "__main__":
    appMain()
