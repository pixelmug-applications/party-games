import { computed, reactive, watch } from 'vue';
import { GAME_CATALOG, gameInfo } from '../gameCatalog';
import { hasJeeWebBridge, loadPixelMug } from '../template/bubbleClient';
import { openMpsApp } from '../template/mpsLaunch';
import { useBleSession } from '../template/bleSession';
import type { AppStatus, DeviceInfo, GameId, HistoryItem } from '../types';

type LaunchPhase = 'idle' | 'requesting' | 'preparing' | 'switching' | 'ready' | 'failed';
type TabId = 'library' | 'history' | 'settings';

const DEFAULT_WHEEL_OPTIONS = ['Pizza', 'Movie', 'Karaoke', 'Coffee'];
const STORAGE_KEY = 'mps-party-games-state-v1';
const MAX_WHEEL_OPTIONS = 10;
const MAX_WHEEL_TEXT = 8;

const saved = loadSavedState();
const state = reactive({
  status: 'idle' as AppStatus,
  message: '',
  device: null as DeviceInfo | null,
  launchPhase: 'idle' as LaunchPhase,
  businessStatus: 'idle' as AppStatus,
  businessMessage: '',
  selectedGame: saved.selectedGame,
  wheelOptions: saved.wheelOptions,
  history: saved.history,
  activeTab: 'library' as TabId,
});

let bleSession: ReturnType<typeof useBleSession> | null = null;

function getBle() {
  if (!bleSession) {
    bleSession = useBleSession();
  }
  return bleSession;
}

const busy = computed(() => ['loading', 'installing', 'connecting', 'syncing'].includes(state.status));
const canSend = computed(() => Boolean(state.device) && getBle().isReady.value);
const canEnter = computed(() => state.launchPhase === 'ready');
const statusText = computed(() => {
  if (!state.message) return '';
  return hasJeeWebBridge() ? state.message : `${state.message} Browser mock mode.`;
});
const openButtonLabel = computed(() => {
  if (busy.value) return 'Opening...';
  if (state.launchPhase === 'ready') return 'Click to Enter';
  if (state.launchPhase === 'failed') return 'Try Again';
  return 'Open on PixelMug';
});
const selectedGameInfo = computed(() => gameInfo(state.selectedGame));
const cleanWheelOptions = computed(() => sanitizeOptions(state.wheelOptions));

watch(
  () => ({
    selectedGame: state.selectedGame,
    wheelOptions: state.wheelOptions,
    history: state.history,
  }),
  (value) => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  },
  { deep: true },
);

export function usePartyGames() {
  async function refreshDevice() {
    state.status = 'loading';
    state.message = 'Loading PixelMug...';
    try {
      const result = await loadPixelMug();
      state.device = result;
      state.status = result ? 'ready' : 'error';
      state.message = result ? 'PixelMug ready.' : 'No PixelMug is bound.';
    } catch (error) {
      state.status = 'error';
      state.message = errorMessage(error);
    }
  }

  async function openOnDevice() {
    if (!state.device) {
      await refreshDevice();
    }

    const target = state.device || (await loadPixelMug());
    if (!target) {
      state.status = 'error';
      state.message = 'No PixelMug is bound.';
      return false;
    }

    state.device = target;
    state.status = 'installing';
    state.launchPhase = 'requesting';
    state.message = 'Opening on PixelMug...';
    try {
      await openMpsApp(target, undefined, {
        onPhase: updateLaunchPhase,
      });
      markLaunchReady();
      return true;
    } catch (error) {
      state.status = 'error';
      state.launchPhase = 'failed';
      state.message = errorMessage(error);
      return false;
    }
  }

  async function connectDevice() {
    const target = state.device || (await loadPixelMug());
    if (!target) {
      state.status = 'error';
      state.message = 'No PixelMug is bound.';
      return;
    }

    state.device = target;
    state.status = 'connecting';
    state.message = 'Connecting BLE...';
    const ble = getBle();
    try {
      await ble.ensureConnected(target);
      state.status = 'connected';
      state.message = 'BLE connected.';
    } catch (error) {
      state.status = 'error';
      state.message = errorMessage(error);
    }
  }

  async function showGame(game: GameId = state.selectedGame) {
    state.selectedGame = game;
    if (!state.device) {
      await refreshDevice();
    }
    if (!state.device) return;

    state.status = 'syncing';
    state.businessStatus = 'syncing';
    state.businessMessage = `Showing ${gameInfo(game).name}...`;

    const ble = getBle();
    try {
      await ble.send(state.device, {
        method: 'mpyPartyGamesSelect',
        id: `party_${Date.now()}`,
        params: {
          game,
          wheelOptions: cleanWheelOptions.value,
        },
      });
      state.status = 'connected';
      state.businessStatus = 'connected';
      state.businessMessage = `${gameInfo(game).name} is on PixelMug.`;
      addHistory(game);
    } catch (error) {
      state.status = 'error';
      state.businessStatus = 'error';
      state.businessMessage = errorMessage(error);
    }
  }

  function selectGame(game: GameId) {
    state.selectedGame = game;
  }

  function setTab(tab: TabId) {
    state.activeTab = tab;
  }

  function addWheelOption() {
    if (state.wheelOptions.length >= MAX_WHEEL_OPTIONS) return;
    state.wheelOptions.push('Option');
    normalizeWheelOptions();
  }

  function removeWheelOption(index: number) {
    if (state.wheelOptions.length <= 1) return;
    state.wheelOptions.splice(index, 1);
    normalizeWheelOptions();
  }

  function normalizeWheelOptions() {
    state.wheelOptions = sanitizeOptions(state.wheelOptions);
  }

  function bindBleState() {
    refreshDevice();
    return getBle().bindState();
  }

  return {
    state,
    busy,
    canSend,
    canEnter,
    statusText,
    openButtonLabel,
    selectedGameInfo,
    cleanWheelOptions,
    gameCatalog: GAME_CATALOG,
    maxWheelOptions: MAX_WHEEL_OPTIONS,
    maxWheelText: MAX_WHEEL_TEXT,
    addWheelOption,
    bindBleState,
    connectDevice,
    normalizeWheelOptions,
    openOnDevice,
    refreshDevice,
    removeWheelOption,
    selectGame,
    setTab,
    showGame,
  };
}

function addHistory(game: GameId) {
  const item: HistoryItem = {
    id: `${Date.now()}_${game}`,
    game,
    label: gameInfo(game).name,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  };
  state.history = [item, ...state.history].slice(0, 10);
}

function markLaunchReady() {
  state.status = 'ready';
  state.launchPhase = 'ready';
  state.message = 'Ready on PixelMug.';
}

function updateLaunchPhase(phase: LaunchPhase) {
  state.launchPhase = phase;
  if (phase === 'requesting') {
    state.message = 'Opening on PixelMug...';
  } else if (phase === 'preparing') {
    state.message = 'Preparing app...';
  } else if (phase === 'switching') {
    state.message = 'Switching app...';
  } else if (phase === 'ready') {
    state.message = 'Ready on PixelMug.';
  }
}

function loadSavedState() {
  const fallback = {
    selectedGame: 'COIN' as GameId,
    wheelOptions: [...DEFAULT_WHEEL_OPTIONS],
    history: [] as HistoryItem[],
  };

  try {
    const raw = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || 'null') as Partial<typeof fallback> | null;
    if (!raw) return fallback;
    return {
      selectedGame: isGame(raw.selectedGame) ? raw.selectedGame : fallback.selectedGame,
      wheelOptions: sanitizeOptions(raw.wheelOptions || fallback.wheelOptions),
      history: Array.isArray(raw.history) ? raw.history.slice(0, 10) : fallback.history,
    };
  } catch {
    return fallback;
  }
}

function sanitizeOptions(options: unknown) {
  const source = Array.isArray(options) ? options : DEFAULT_WHEEL_OPTIONS;
  const cleaned: string[] = [];
  for (const item of source) {
    const text = String(item || '').trim().slice(0, MAX_WHEEL_TEXT);
    if (text && cleaned.length < MAX_WHEEL_OPTIONS) cleaned.push(text);
  }
  return cleaned.length ? cleaned : [...DEFAULT_WHEEL_OPTIONS];
}

function isGame(value: unknown): value is GameId {
  return GAME_CATALOG.some((game) => game.id === value);
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error || 'Unknown error');
}
