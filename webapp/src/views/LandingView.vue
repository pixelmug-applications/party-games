<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { LANDING_LOGO, LANDING_VIDEO } from '../assets';
import { usePartyGames } from '../state/partyGames';

type LandingStep = 'open' | 'enter';

const router = useRouter();
const store = usePartyGames();
const step = ref<LandingStep>('open');

async function handleOpen() {
  const ok = await store.openOnDevice();
  step.value = ok ? 'enter' : 'open';
}

async function handleEnter() {
  if (!store.canEnter.value) {
    await handleOpen();
    return;
  }
  router.push('/games');
  await store.connectDevice();
}
</script>

<template>
  <main class="landing" :class="step">
    <video class="landing-video" :src="LANDING_VIDEO" autoplay muted loop playsinline />
    <div class="landing-shade" />

    <section class="landing-panel">
      <img class="landing-logo" :src="LANDING_LOGO" alt="Party Games" />
      <h1>Party Games</h1>
      <p>Choose a mini game, push it to PixelMug, and keep the table moving.</p>
    </section>

    <div class="landing-actions">
      <button class="landing-primary" :disabled="store.busy.value" @click="step === 'enter' ? handleEnter() : handleOpen()">
        {{ store.openButtonLabel.value }}
      </button>
      <p
        v-if="store.statusText.value"
        :class="store.state.status === 'error' ? 'landing-error' : 'landing-status'"
      >
        {{ store.statusText.value }}
      </p>
    </div>
  </main>
</template>
