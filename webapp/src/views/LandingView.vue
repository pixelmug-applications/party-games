<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { LANDING_LOGO, LANDING_VIDEO } from '../assets';
import { usePartyGames } from '../state/partyGames';

type LandingStep = 'open' | 'enter';

const router = useRouter();
const store = usePartyGames();
const step = ref<LandingStep>('open');
const landingVideo = ref<HTMLVideoElement | null>(null);
let opening = false;

async function handleOpen() {
  if (opening) return;
  opening = true;
  try {
    const ok = await store.openOnDevice();
    step.value = ok ? 'enter' : 'open';
    if (ok) void store.connectDevice();
  } finally {
    opening = false;
  }
}

onMounted(() => {
  void handleOpen();
  void nextTick(loadLandingVideo);
});

function loadLandingVideo() {
  const video = landingVideo.value;
  if (!video) return;
  video.muted = true;
  video.load();
  playLandingVideo('initial-load');
}

function playLandingVideo(source: string) {
  const video = landingVideo.value;
  if (!video) return;
  video.muted = true;
  video.play().catch((error: unknown) => {
    console.warn('[PartyGames] background video play rejected', {
      source,
      error: error instanceof Error ? error.message : String(error),
      readyState: video.readyState,
      networkState: video.networkState,
      currentSrc: video.currentSrc,
    });
  });
}

function handleLandingVideoError() {
  const video = landingVideo.value;
  console.error('[PartyGames] background video error', {
    currentSrc: video?.currentSrc || LANDING_VIDEO,
    mediaError: video?.error
      ? { code: video.error.code, message: video.error.message }
      : null,
    readyState: video?.readyState,
    networkState: video?.networkState,
  });
}

async function handleEnter() {
  if (!store.canEnter.value) {
    await handleOpen();
    return;
  }
  router.push('/games');
}
</script>

<template>
  <main class="landing" :class="step">
    <video
      ref="landingVideo"
      class="landing-video"
      :src="LANDING_VIDEO"
      autoplay
      muted
      loop
      playsinline
      webkit-playsinline
      preload="auto"
      @loadeddata="playLandingVideo('loadeddata')"
      @canplay="playLandingVideo('canplay')"
      @error="handleLandingVideoError"
    />
    <div class="landing-shade" aria-hidden="true" />
    <section class="landing-panel">
      <img class="landing-logo" :src="LANDING_LOGO" alt="Party Games" />
      <h1>Party Games</h1>
      <p>Choose a mini game, push it to PixelMug, and keep the table moving.</p>
    </section>

    <div class="landing-actions">
      <button class="landing-primary" :disabled="step === 'open' && store.busy.value" @click="step === 'enter' ? handleEnter() : handleOpen()">
        {{ step === 'enter' ? 'Click to Enter' : store.openButtonLabel.value }}
      </button>
      <p
        v-if="step === 'enter' || store.statusText.value"
        :class="step === 'open' && store.state.status === 'error' ? 'landing-error' : 'landing-status'"
      >
        {{ step === 'enter' ? 'Ready on PixelMug.' : store.statusText.value }}
      </p>
    </div>
  </main>
</template>
