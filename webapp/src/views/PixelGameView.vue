<script setup lang="ts">
import { computed } from 'vue';
import type { FunctionalComponent } from 'vue';
import {
  BookOpen,
  CircleDot,
  CircleGauge,
  Coins,
  Dice5,
  Hand,
  History,
  ListRestart,
  Settings,
} from 'lucide-vue-next';
import { gameInfo, type GameIconKey } from '../gameCatalog';
import { usePartyGames } from '../state/partyGames';
import type { GameId } from '../types';

type IconComponent = FunctionalComponent<Record<string, unknown>>;

const gameIcons: Record<GameIconKey, IconComponent> = {
  coin: Coins,
  dice: Dice5,
  rps: Hand,
  roulette: CircleGauge,
  wheel: CircleDot,
};

const store = usePartyGames();
const selected = computed(() => store.state.selectedGame);
const isWheelSelected = computed(() => selected.value === 'WHEEL');
const canAddOption = computed(() => store.state.wheelOptions.length < store.maxWheelOptions);

function selectGame(game: GameId) {
  store.selectGame(game);
}

function showSelected() {
  store.showGame(selected.value);
}

function iconForGame(game: GameId) {
  return gameIcons[gameInfo(game).iconKey];
}

function historyTime(time: string) {
  return time || '--:--:--';
}
</script>

<template>
  <main class="miniapp">
    <section v-if="store.state.activeTab === 'library'" class="tab-page library-page">
      <header class="page-header">
        <p>Library</p>
        <h1>Pixel Game App</h1>
      </header>

      <div class="game-grid">
        <button
          v-for="game in store.gameCatalog"
          :key="game.id"
          type="button"
          class="game-card"
          :class="{ selected: selected === game.id }"
          :style="{ '--accent': game.accent }"
          @click="selectGame(game.id)"
        >
          <span class="game-icon" aria-hidden="true">
            <component :is="gameIcons[game.iconKey]" :size="54" :stroke-width="2.2" />
          </span>
          <span class="game-name">{{ game.name }}</span>
          <span class="game-subtitle">{{ game.subtitle }}</span>
        </button>
      </div>

      <section v-if="isWheelSelected" class="wheel-summary">
        <div>
          <strong>Wheel Options</strong>
          <p>{{ store.cleanWheelOptions.value.join(' / ') }}</p>
        </div>
        <button type="button" @click="store.setTab('settings')">Edit</button>
      </section>
    </section>

    <section v-else-if="store.state.activeTab === 'history'" class="tab-page history-page compact-page">
      <header class="history-header">
        <span>Recent Decisions</span>
        <button type="button" :disabled="!store.state.history.length" @click="store.clearHistory">Clear all</button>
      </header>

      <div v-if="store.state.history.length" class="decision-list">
        <article v-for="item in store.state.history" :key="item.id" class="decision-row">
          <span class="decision-icon" :style="{ backgroundColor: gameInfo(item.game).accent }" aria-hidden="true">
            <component :is="iconForGame(item.game)" :size="22" :stroke-width="2.4" />
          </span>
          <div class="decision-main">
            <strong>{{ item.label }}</strong>
            <p>{{ historyTime(item.time) }}</p>
          </div>
          <strong class="decision-result">{{ item.result }}</strong>
        </article>
      </div>
      <p v-else class="empty-note">No decisions yet.</p>
    </section>

    <section v-else class="tab-page settings-page">
      <header class="page-header">
        <p>Settings</p>
        <h1>Decision Wheel</h1>
      </header>

      <div class="settings-card">
        <div class="settings-title">
          <div>
            <strong>Options</strong>
            <p>Up to {{ store.maxWheelOptions }} items, {{ store.maxWheelText }} characters each.</p>
          </div>
          <button type="button" :disabled="!canAddOption" @click="store.addWheelOption">Add</button>
        </div>

        <div class="option-list">
          <label v-for="(_, index) in store.state.wheelOptions" :key="index" class="option-row">
            <span>{{ index + 1 }}</span>
            <input
              v-model="store.state.wheelOptions[index]"
              :maxlength="store.maxWheelText"
              @blur="store.normalizeWheelOptions"
            />
            <button type="button" :disabled="store.state.wheelOptions.length <= 1" @click="store.removeWheelOption(index)">x</button>
          </label>
        </div>
      </div>
    </section>
    <button v-if="store.state.activeTab !== 'history'" class="show-wide" :disabled="store.busy.value" type="button" @click="showSelected">
      Show {{ store.selectedGameInfo.value.name }}
    </button>

    <nav class="bottom-tabs">
      <button type="button" aria-label="Library" :class="{ active: store.state.activeTab === 'library' }" @click="store.setTab('library')">
        <BookOpen :size="30" :stroke-width="2.3" />
      </button>
      <button type="button" aria-label="History" :class="{ active: store.state.activeTab === 'history' }" @click="store.setTab('history')">
        <History :size="30" :stroke-width="2.3" />
      </button>
      <button type="button" aria-label="Settings" :class="{ active: store.state.activeTab === 'settings' }" @click="store.setTab('settings')">
        <Settings :size="30" :stroke-width="2.3" />
      </button>
    </nav>
  </main>
</template>
