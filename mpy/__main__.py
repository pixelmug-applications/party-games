import json
import time

import micropyxel as pyxel

from ble_webapp import WebAppBleManager
import dice_roll
import flip_coin
import rps
import rr
import wheel
from dice_roll import DiceRollApp
from flip_coin import FlipCoinApp
from rps import RpsApp
from rr import RussianRouletteApp
from wheel import SlotWheelApp


FPS = 30
APP_NAME = "PartyGames"
MAX_WHEEL_OPTIONS = 10
MAX_WHEEL_TEXT = 8
MAX_HISTORY = 5
HISTORY_PATH = "party_history.jsonl"

GAME_COIN = "COIN"
GAME_DICE = "DICE"
GAME_RPS = "RPS"
GAME_ROULETTE = "ROULETTE"
GAME_WHEEL = "WHEEL"

DEFAULT_WHEEL_OPTIONS = ("Pizza", "Movie", "Karaoke", "Coffee")

GAME_CLASSES = {
    GAME_COIN: FlipCoinApp,
    GAME_DICE: DiceRollApp,
    GAME_RPS: RpsApp,
    GAME_ROULETTE: RussianRouletteApp,
    GAME_WHEEL: SlotWheelApp,
}

GAME_ALIASES = {
    "FLIP_COIN": GAME_COIN,
    "COIN": GAME_COIN,
    "DICE_ROLL": GAME_DICE,
    "DICE": GAME_DICE,
    "RPS": GAME_RPS,
    "RR": GAME_ROULETTE,
    "ROULETTE": GAME_ROULETTE,
    "RUSSIAN_ROULETTE": GAME_ROULETTE,
    "WHEEL": GAME_WHEEL,
}

RPS_NAMES = {
    rps.PAPER: "PAPER",
    rps.SCISSORS: "SCISSORS",
    rps.ROCK: "ROCK",
}


class PartyGamesRouter:
    def __init__(self):
        self.ble = WebAppBleManager(APP_NAME, self.handleBleMessage)
        self.current_game = None
        self.current_game_id = None
        self.pending_game_id = GAME_COIN
        self.wheel_options = list(DEFAULT_WHEEL_OPTIONS)
        self.pyxel_ready = False
        self.last_state = None
        self.last_connected = False
        self.history = self._load_history()
        self.next_record_id = len(self.history) + 1
        self._switch_to(GAME_COIN)

    def appUpdate(self, rt):
        self.ble.poll()
        self._sync_history_on_connect()
        if self.pending_game_id is not None:
            game_id = self.pending_game_id
            self.pending_game_id = None
            self._switch_to(game_id)

        if self.current_game is not None:
            prev_state = getattr(self.current_game, "state", None)
            self.current_game.appUpdate(rt)
            self._capture_result(prev_state, getattr(self.current_game, "state", None))

    def appDraw(self, rt):
        if self.current_game is not None:
            self.current_game.appDraw(rt)

    def appOnExit(self, rt, reason, exc):
        try:
            if self.current_game is not None:
                self.current_game.appOnExit(rt, reason, exc)
            else:
                pyxel.destroy()
        except Exception:
            pass
        self.ble.deinit()

    def handleBleMessage(self, conn, message):
        try:
            method = message.get("method")
            request_id = message.get("id")
            if method == "mpyPing":
                self.ble.reply(request_id, True, conn=conn)
                self._send_history(conn=conn)
                return
            if method == "mpyPartyGamesGetHistory":
                self.ble.reply(request_id, True, conn=conn)
                self._send_history(conn=conn)
                return
            if method == "mpyPartyGamesClearHistory":
                self.history = []
                self._save_history()
                self.ble.reply(request_id, True, conn=conn)
                self._send_history(conn=conn)
                return
            if method != "mpyPartyGamesSelect":
                return

            params = message.get("params") or {}
            game_id = self._normalize_game(params.get("game"))
            if game_id is None:
                self.ble.reply(request_id, False, "Unknown game", conn=conn)
                return

            self.wheel_options = self._sanitize_options(params.get("wheelOptions"))
            self.pending_game_id = game_id
            self.ble.reply(request_id, True, conn=conn)
            self.ble.send({"event": "partyGamesSelected", "game": game_id}, conn=conn)
        except Exception as exc:
            print("[PartyGames] receive error:", exc)
            self.ble.reply(None, False, str(exc), conn=conn)

    def _switch_to(self, game_id):
        cls = GAME_CLASSES.get(game_id)
        if cls is None:
            return

        print("[PartyGames] switch", game_id)
        self.current_game = self._build_game(cls)
        self.current_game_id = game_id
        self.last_state = getattr(self.current_game, "state", None)
        if game_id == GAME_WHEEL:
            self.current_game.set_options(self.wheel_options)

    def _build_game(self, cls):
        if not self.pyxel_ready:
            app = cls()
            self.pyxel_ready = True
            return app

        original_init = pyxel.init
        try:
            pyxel.init = _noop
            return cls()
        finally:
            pyxel.init = original_init

    def _capture_result(self, prev_state, next_state):
        if prev_state == next_state:
            return

        game_id = self.current_game_id
        app = self.current_game
        record = None

        if game_id == GAME_COIN and next_state == flip_coin.STATE_DONE:
            result = "HEADS" if app.current_face == flip_coin.FACE_FRONT else "TAILS"
            record = self._make_record(game_id, "Coin Flip", result)
        elif game_id == GAME_DICE and next_state == dice_roll.STATE_DONE:
            record = self._make_record(game_id, "Dice Roll", str(app.current_face + 1))
        elif game_id == GAME_RPS and next_state == rps.STATE_DONE:
            record = self._make_record(game_id, "RPS", RPS_NAMES.get(app.current_item, "ROCK"))
        elif game_id == GAME_ROULETTE and next_state == rr.STATE_SHOT:
            record = self._make_record(game_id, "Russian Roulette", "R%d" % app.round_no)
        elif game_id == GAME_WHEEL and next_state == wheel.STATE_DONE:
            result = app.options[app.result_index] if app.options else ""
            record = self._make_record(game_id, "Decision Wheel", result)

        if record is not None:
            self._append_record(record)
            self._send_history()

    def _make_record(self, game_id, label, result):
        try:
            tick = time.ticks_ms()
        except Exception:
            tick = 0
        record_id = "%d_%d" % (tick, self.next_record_id)
        self.next_record_id += 1
        return {
            "id": record_id,
            "game": game_id,
            "label": label,
            "result": str(result),
            "time": self._time_text(),
            "tick": tick,
        }

    def _append_record(self, record):
        next_history = []
        for item in self.history:
            if item.get("game") != record.get("game"):
                next_history.append(item)
        next_history.append(record)
        self.history = self._sort_history(next_history)[-MAX_HISTORY:]
        self._save_history()

    def _load_history(self):
        records = []
        try:
            with open(HISTORY_PATH, "r") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                        if isinstance(item, dict) and item.get("id"):
                            records.append(item)
                    except Exception:
                        pass
        except Exception:
            pass
        by_game = {}
        for record in records:
            game = record.get("game")
            if game:
                by_game[game] = record
        return self._sort_history(list(by_game.values()))[-MAX_HISTORY:]

    def _save_history(self):
        try:
            with open(HISTORY_PATH, "w") as fp:
                for record in self._sort_history(self.history)[-MAX_HISTORY:]:
                    fp.write(json.dumps(record))
                    fp.write("\n")
        except Exception as exc:
            print("[PartyGames] history save failed:", exc)

    def _send_history(self, conn=None):
        if not self.ble.connected and conn is None:
            return
        self.ble.send({"event": "partyGamesHistory", "records": self._sort_history(self.history)[-MAX_HISTORY:]}, conn=conn)

    def _sync_history_on_connect(self):
        connected = self.ble.connected
        if connected and not self.last_connected:
            self._send_history()
        self.last_connected = connected

    def _sort_history(self, records):
        return sorted(records, key=lambda item: item.get("tick", 0))

    def _time_text(self):
        try:
            now = time.localtime()
            return "%02d:%02d:%02d" % (now[3], now[4], now[5])
        except Exception:
            return ""

    def _normalize_game(self, value):
        key = str(value or "").strip().upper()
        return GAME_ALIASES.get(key)

    def _sanitize_options(self, options):
        cleaned = []
        if isinstance(options, (list, tuple)):
            source = options
        else:
            source = DEFAULT_WHEEL_OPTIONS

        for item in source:
            text = str(item or "").strip()
            if text and len(cleaned) < MAX_WHEEL_OPTIONS:
                cleaned.append(text[:MAX_WHEEL_TEXT])

        if not cleaned:
            return list(DEFAULT_WHEEL_OPTIONS)
        return cleaned


def _noop(*_args, **_kwargs):
    return None


def appMain():
    app = PartyGamesRouter()
    app.ble.start()
    pyxel.run(app.appUpdate, app.appDraw, fps=FPS, on_exit=app.appOnExit)


if __name__ == "__main__":
    appMain()
