import time

import micropyxel as pyxel
from simpletouch import SimpleTouch


FPS = 30
SCREEN_W = 32
SCREEN_H = 16
TOUCH_PIN = 38

COL_BLACK = 0
COL_WHITE = 7
COL_TEXT = COL_WHITE
COL_BORDER = 10
COL_CHASE = COL_WHITE
COL_FLASH_GREEN = 11
COL_FLASH_CYAN = 12
COL_FLASH_RED = 8
FLASH_STEP_FRAMES = 5
CHASE_SPEED = 2
OPTION_COLOR_POOL = (8, 9, 11, 12, 14, 15, 6, 13, 3, 5)
MAX_OPTIONS = 10
SPIN_BASE_OPTION_COUNT = 4
SPIN_EXTRA_FRAMES_PER_OPTION = FPS // 5

FONT_W = 4
FONT_H = 6
FRAME_X = 0
FRAME_Y = 3
FRAME_W = 32
FRAME_H = 10
FRAME_INNER_X = FRAME_X + 1
FRAME_INNER_Y = FRAME_Y + 1
FRAME_INNER_W = FRAME_W - 2
FRAME_INNER_H = FRAME_H - 2
TEXT_HOME_Y = FRAME_INNER_Y + ((FRAME_INNER_H - FONT_H) // 2)
ITEM_SPACING = FRAME_H

STATE_IDLE = 0
STATE_SPINNING = 1
STATE_DONE = 2

START_OPTION_TEXT = "? ? ?"

DEFAULT_OPTIONS = ("red", "blue", "green", "pink")


class SlotWheelApp:
    def __init__(self):
        pyxel.init()
        self.rng_state = self._make_seed()

        self.touch = SimpleTouch(pin_no=TOUCH_PIN, active_high=True)

        self.config = {
            "options": list(DEFAULT_OPTIONS),
            "spin_frames": FPS * 4,
        }

        self.options = []
        self.option_colors = []
        self.item_count = 0
        self.offset_q8 = 0
        self.start_offset_q8 = 0
        self.target_offset_q8 = 0
        self.speed_q8 = 0
        self.frame = 0
        self.spin_frame = 0
        self.spin_total = self.config["spin_frames"]
        self.target_index = 0
        self.result_index = 0
        self.state = STATE_IDLE

        self.set_options(self.config["options"])
        self._align_to_option(0)

    def set_options(self, options):
        cleaned = []
        for item in options:
            text = str(item).strip()
            if text and len(cleaned) < MAX_OPTIONS:
                cleaned.append(text[:8])

        if not cleaned:
            cleaned = list(DEFAULT_OPTIONS)

        self.config["options"] = cleaned
        self.options = cleaned
        self.item_count = len(cleaned)
        self.option_colors = self._make_option_colors(self.item_count)
        self.result_index = self.result_index % self.item_count

    def start_spin(self):
        if self.item_count <= 0:
            return

        self._mix_rng(self.frame + self.offset_q8 + (self.result_index << 8))
        self.state = STATE_SPINNING
        self.spin_frame = 0
        extra_frames = self._spin_extra_frames()
        self.spin_total = self.config["spin_frames"] + extra_frames + self._rand_int(-12, 18)
        if self.spin_total < FPS * 2:
            self.spin_total = FPS * 2

        self.start_offset_q8 = self.offset_q8
        current_slot = self._nearest_slot_index()
        self.target_index = self._rand_int(0, self.item_count - 1)
        if self.item_count > 1 and self.target_index == current_slot:
            self.target_index = (self.target_index + self._rand_int(1, self.item_count - 1)) % self.item_count
        loops = self.item_count * self._rand_int(7, 10)
        advance = loops + ((self.target_index - current_slot) % self.item_count)
        self.target_offset_q8 = self.offset_q8 + advance * ITEM_SPACING * 256

    def appUpdate(self, _rt):
        self.frame += 1
        self._update_touch()

        if self.state == STATE_SPINNING:
            self._update_spin()

    def appDraw(self, _rt):
        pyxel.cls(COL_BLACK)
        self._draw_frame()
        self._draw_wheel()

    def _draw_frame(self):
        pyxel.rect(FRAME_X, FRAME_Y, FRAME_W, FRAME_H, COL_BLACK)
        if self.state == STATE_SPINNING:
            pyxel.rectb(FRAME_X, FRAME_Y, FRAME_W, FRAME_H, self._slot_flash_color())
            self._draw_slot_chase_light()
        else:
            pyxel.rectb(FRAME_X, FRAME_Y, FRAME_W, FRAME_H, COL_BORDER)

    def _slot_flash_color(self):
        phase = (self.spin_frame // FLASH_STEP_FRAMES) % 3
        if phase == 0:
            return COL_FLASH_GREEN
        if phase == 1:
            return COL_FLASH_CYAN
        return COL_FLASH_RED

    def _draw_slot_chase_light(self):
        x0 = FRAME_X
        y0 = FRAME_Y
        x1 = FRAME_X + FRAME_W - 1
        y1 = FRAME_Y + FRAME_H - 1
        count = (self.spin_frame * CHASE_SPEED) % ((FRAME_W - 3) * 2 + (FRAME_H - 2) * 2)

        if count < FRAME_W - 3:
            pyxel.rect(x0 + count, y0, 3, 1, COL_CHASE)
            return

        count -= FRAME_W - 3
        if count < FRAME_H - 2:
            pyxel.rect(x1, y0 + count, 1, 2, COL_CHASE)
            return

        count -= FRAME_H - 2
        if count < FRAME_W - 3:
            pyxel.rect(x1 - count - 2, y1, 3, 1, COL_CHASE)
            return

        count -= FRAME_W - 3
        pyxel.rect(x0, y1 - count - 1, 1, 2, COL_CHASE)

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
                if self.state != STATE_SPINNING:
                    self.start_spin()

    def _update_spin(self):
        self.spin_frame += 1

        if self.spin_frame >= self.spin_total:
            self.offset_q8 = self.target_offset_q8
            self.speed_q8 = 0
            self.result_index = self.target_index
            self.state = STATE_DONE
            return

        distance = self.target_offset_q8 - self.start_offset_q8
        t = (self.spin_frame * 1024) // self.spin_total
        inv = 1024 - t
        eased = 1024 - ((inv * inv * inv) // (1024 * 1024))
        next_offset = self.start_offset_q8 + ((distance * eased) // 1024)

        self.speed_q8 = next_offset - self.offset_q8
        self.offset_q8 = next_offset

    def _draw_wheel(self):
        if self.item_count <= 0:
            return

        if self.state == STATE_IDLE:
            self._draw_option(START_OPTION_TEXT, TEXT_HOME_Y, COL_TEXT)
            return

        base = (self.offset_q8 // 256) % ITEM_SPACING
        first_slot = (self.offset_q8 // (ITEM_SPACING * 256)) % self.item_count

        for n in range(-1, self.item_count + 3):
            idx = (first_slot + n) % self.item_count
            y = TEXT_HOME_Y - n * ITEM_SPACING + base
            if y <= FRAME_INNER_Y - FONT_H or y >= FRAME_INNER_Y + FRAME_INNER_H:
                continue
            self._draw_option(self.options[idx], y, self.option_colors[idx])

    def _draw_option(self, text, y, color):
        x = self._text_x(text)

        pyxel.clip(FRAME_INNER_X, FRAME_INNER_Y, FRAME_INNER_W, FRAME_INNER_H)
        pyxel.text(x, y, text, color)
        pyxel.clip()

    def _make_option_colors(self, count):
        pool = list(OPTION_COLOR_POOL)
        for i in range(len(pool) - 1, 0, -1):
            j = self._rand_int(0, i)
            pool[i], pool[j] = pool[j], pool[i]

        colors = []
        while len(colors) < count:
            for color in pool:
                colors.append(color)
                if len(colors) >= count:
                    break
        return colors

    def _spin_extra_frames(self):
        extra_options = self.item_count - SPIN_BASE_OPTION_COUNT
        if extra_options <= 0:
            return 0
        return extra_options * SPIN_EXTRA_FRAMES_PER_OPTION

    def _align_to_option(self, index):
        self.result_index = index % self.item_count
        self.offset_q8 = self.result_index * ITEM_SPACING * 256
        self.start_offset_q8 = self.offset_q8
        self.target_offset_q8 = self.offset_q8

    def _nearest_slot_index(self):
        slot_q8 = ITEM_SPACING * 256
        return ((self.offset_q8 + slot_q8 // 2) // slot_q8) % self.item_count

    def _text_x(self, text):
        width = len(text) * FONT_W
        x = (SCREEN_W - width) // 2
        if x < 0:
            return 0
        return x

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
    app = SlotWheelApp()
    pyxel.run(app.appUpdate, app.appDraw, fps=FPS, on_exit=app.appOnExit)


if __name__ == "__main__":
    appMain()