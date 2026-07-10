import time

import micropyxel as pyxel
import mpy_button as touch_events


FPS = 30
SCREEN_W = 32
SCREEN_H = 16

COL_BLACK = 0
COLKEY = COL_BLACK

COIN_BANK = 0
COIN_ASSET_PATH = "assets/sprites.png"

FACE_FRONT = 0
FACE_BACK = 1

FRAMES_PER_HALF_TURN = 8
FAST_SPIN_MIN_FRAMES = FPS * 3
FAST_SPIN_MAX_FRAMES = FPS * 5
RAMP_UP_FRAMES = FPS // 2
RAMP_DOWN_FRAMES = FPS * 4
FAST_STEPS_PER_FRAME = 4
SLOW_STEP_WAIT_FRAMES = 5

STATE_IDLE = 0
STATE_FLIPPING = 1
STATE_DONE = 2

# (src_x, src_y, width, height), inclusive sprite coordinates converted to size.
FRONT_TO_BACK = (
    (0, 45, 15, 15),
    (17, 45, 13, 15),
    (32, 45, 12, 15),
    (46, 45, 10, 15),
    (58, 45, 4, 15),
    (64, 45, 10, 15),
    (76, 45, 12, 15),
    (92, 45, 13, 15),
)

BACK_TO_FRONT = (
    (0, 63, 15, 15),
    (17, 63, 13, 15),
    (32, 63, 12, 15),
    (46, 63, 10, 15),
    (58, 63, 4, 15),
    (64, 63, 10, 15),
    (76, 63, 12, 15),
    (92, 63, 13, 15),
)


class FlipCoinApp:
    def __init__(self, touch_enabled=True):
        pyxel.init()
        pyxel.images(COIN_BANK).load_from_png(0, 0, COIN_ASSET_PATH, True)

        self.touch = touch_events if touch_enabled else None
        if self.touch is not None:
            self.touch.clear()
        self.rng_state = self._make_seed()

        self.frame = 0
        self.flip_frame = 0
        self.current_face = FACE_FRONT
        self.start_face = FACE_FRONT
        self.target_face = FACE_FRONT
        self.total_steps = 0
        self.steps_done = 0
        self.state = STATE_IDLE

    def start_flip(self):
        self._mix_rng(self.frame + (self.current_face << 8) + self.flip_frame)

        self.state = STATE_FLIPPING
        self.flip_frame = 0
        self.steps_done = 0

        self.start_face = self.current_face
        self.target_face = self._rand_int(FACE_FRONT, FACE_BACK)
        self.fast_spin_frames = self._rand_int(FAST_SPIN_MIN_FRAMES, FAST_SPIN_MAX_FRAMES)
        face_advance = (self.target_face - self.start_face) & 1
        base_steps = self._planned_steps()
        half_turns = base_steps // FRAMES_PER_HALF_TURN
        if (half_turns & 1) != face_advance:
            half_turns -= 1
        if half_turns < 1:
            half_turns = 1 + face_advance
        self.total_steps = half_turns * FRAMES_PER_HALF_TURN

    def appUpdate(self, _rt):
        self.frame += 1
        self._update_touch()

        if self.state == STATE_FLIPPING:
            self._update_flip()

    def appDraw(self, _rt):
        pyxel.cls(COL_BLACK)
        self._draw_coin()

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
            if self.state != STATE_FLIPPING:
                self.start_flip()

    def _update_flip(self):
        self.flip_frame += 1
        self.steps_done += self._steps_this_frame(self.flip_frame)

        if self.steps_done >= self.total_steps:
            self.steps_done = self.total_steps
            self.current_face = self.target_face
            self.state = STATE_DONE
            return

        half_turn = self.steps_done // FRAMES_PER_HALF_TURN
        self.current_face = (self.start_face + half_turn) & 1

    def _planned_steps(self):
        total_frames = RAMP_UP_FRAMES + self.fast_spin_frames + RAMP_DOWN_FRAMES
        steps = 0
        for frame_no in range(1, total_frames + 1):
            steps += self._steps_this_frame(frame_no)
        return steps

    def _steps_this_frame(self, frame_no):
        if frame_no <= RAMP_UP_FRAMES:
            return 1 + (((FAST_STEPS_PER_FRAME - 1) * frame_no * frame_no) // (RAMP_UP_FRAMES * RAMP_UP_FRAMES))

        fast_end = RAMP_UP_FRAMES + self.fast_spin_frames
        if frame_no <= fast_end:
            return FAST_STEPS_PER_FRAME

        slow_frame = frame_no - fast_end
        if slow_frame <= RAMP_DOWN_FRAMES:
            remain = RAMP_DOWN_FRAMES - slow_frame + 1
            if remain <= SLOW_STEP_WAIT_FRAMES:
                return 1 if (remain == 1 or (frame_no % SLOW_STEP_WAIT_FRAMES) == 0) else 0
            return 1 + (((FAST_STEPS_PER_FRAME - 1) * remain * remain) // (RAMP_DOWN_FRAMES * RAMP_DOWN_FRAMES))

        return 0

    def _draw_coin(self):
        src_x, src_y, w, h = self._coin_sprite()
        x = (SCREEN_W - w) // 2
        y = (SCREEN_H - h) // 2
        pyxel.blt(x, y, COIN_BANK, src_x, src_y, w, h, COLKEY)

    def _coin_sprite(self):
        if self.state != STATE_FLIPPING:
            if self.current_face == FACE_FRONT:
                return FRONT_TO_BACK[0]
            return BACK_TO_FRONT[0]

        step = self.steps_done % FRAMES_PER_HALF_TURN
        half_turn = self.steps_done // FRAMES_PER_HALF_TURN
        face = (self.start_face + half_turn) & 1
        if face == FACE_FRONT:
            return FRONT_TO_BACK[step]
        return BACK_TO_FRONT[step]

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
    app = FlipCoinApp()
    pyxel.run(app.appUpdate, app.appDraw, fps=FPS, on_exit=app.appOnExit)


if __name__ == "__main__":
    appMain()
