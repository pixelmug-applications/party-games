import audio_service
from pyxel_prompt_sound import PromptSoundPlayer


ASSET_ROOT = "assets"
SOUND_VOLUME = 100
SOUND_PACKETS_PER_UPDATE = 4


class PartySound:
    def __init__(self, output_volume=SOUND_VOLUME, asset_root=ASSET_ROOT, debug=False):
        self.audio = audio_service.audio
        self.output_volume = output_volume
        self.initialized = False
        self.last_error = None
        self.player = PromptSoundPlayer(
            audio=self.audio,
            asset_root=asset_root,
            debug=debug,
            log_prefix="[PartySound]",
            stop_handler=lambda player: player.cancel(),
        )

    def ensure_audio(self):
        if self.initialized:
            return True
        try:
            self.audio.init(
                enable_input=False,
                enable_output=True,
                with_opus_encoder=False,
                with_opus_decoder=True,
            )
            self.audio.configure(output_volume=self.output_volume, input_gain=1.0)
            self.initialized = True
            return True
        except Exception as exc:
            self.last_error = exc
            print("[PartySound] audio init failed:", exc)
            return False

    def preload_many(self, paths):
        if not self.ensure_audio():
            return False
        return self.player.preload_many(paths)

    def play(self, path, interrupt=True):
        if not self.ensure_audio():
            return False
        ok = self.player.play(path, interrupt=interrupt)
        if not ok:
            self.last_error = self.player.last_error
            print("[PartySound] play failed:", path, self.last_error)
        return ok

    def update(self, budget_packets=SOUND_PACKETS_PER_UPDATE):
        self.player.update(budget_packets=budget_packets)

    def stop(self):
        return self.player.stop()

    def deinit(self):
        try:
            self.player.deinit()
        except Exception:
            pass
        if self.initialized:
            try:
                self.audio.deinit()
            except Exception:
                pass
            self.initialized = False
