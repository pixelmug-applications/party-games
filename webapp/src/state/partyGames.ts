import { computed, reactive, watch } from 'vue';
import { GAME_CATALOG, gameInfo } from '../gameCatalog';
import { hasJeeWebBridge, loadPixelMug } from '../template/bubbleClient';
import { openMpsApp } from '../template/mpsLaunch';
import { useBleSession, type BleDataEvent } from '../template/bleSession';
import type { AppStatus, DeviceInfo, GameId, HistoryItem } from '../types';

type LaunchPhase = 'idle' | 'requesting' | 'preparing' | 'switching' | 'ready' | 'failed';
type TabId = 'library' | 'history' | 'settings';

const DEFAULT_WHEEL_OPTIONS = ['Pizza', 'Movie', 'Karaoke', 'Coffee'];
const STORAGE_KEY = 'mps-party-games-state-v1';
const MAX_WHEEL_OPTIONS = 10;
const MAX_WHEEL_TEXT = 8;
const MAX_HISTORY = 5;

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
      await requestHistory();
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
    } catch (error) {
      state.status = 'error';
      state.businessStatus = 'error';
      state.businessMessage = errorMessage(error);
    }
  }

  async function requestHistory() {
    if (!state.device || !getBle().isReady.value) return;
    try {
      const response = await getBle().send(state.device, {
        method: 'mpyPartyGamesGetHistory',
        id: `history_${Date.now()}`,
      });
      mergeHistory(responsePayload(response)?.records);
    } catch {
      // History sync is best-effort and should not block the game controls.
    }
  }

  async function clearHistory() {
    state.history = [];
    if (!state.device || !getBle().isReady.value) return;
    try {
      await getBle().send(state.device, {
        method: 'mpyPartyGamesClearHistory',
        id: `clear_${Date.now()}`,
      });
    } catch {
      // Keep the UI cleared even if the device is currently unavailable.
    }
  }

  function selectGame(game: GameId) {
    state.selectedGame = game;
  }

  function setTab(tab: TabId) {
    state.activeTab = tab;
    if (tab === 'history') {
      requestHistory();
    }
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
    const ble = getBle();
    const cleanupState = ble.bindState();
    const cleanupData = ble.bindData(handleBleData);
    return () => {
      cleanupState();
      cleanupData();
    };
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
    clearHistory,
    connectDevice,
    normalizeWheelOptions,
    openOnDevice,
    refreshDevice,
    removeWheelOption,
    requestHistory,
    selectGame,
    setTab,
    showGame,
  };
}

function handleBleData(event: BleDataEvent) {
  const message = event.message as Record<string, unknown> | undefined;
  if (!message) return;
  if (message.event === 'partyGamesHistory') {
    mergeHistory(message.records);
  } else if (message.event === 'partyGamesResult') {
    mergeHistory([message.record]);
  }
}

function responsePayload(response: unknown) {
  const item = response as any;
  return item?.result?.result || item?.result?.message || item?.message || item?.result || response;
}

function mergeHistory(records: unknown) {
  if (!Array.isArray(records)) return;
  const existing = new Map<GameId, HistoryItem>();
  for (const item of state.history) {
    existing.set(item.game, item);
  }

  for (const raw of records) {
    const item = normalizeHistoryItem(raw);
    if (item) existing.set(item.game, item);
  }

  state.history = Array.from(existing.values())
    .sort((a, b) => historyOrderValue(b) - historyOrderValue(a))
    .slice(0, MAX_HISTORY);
}

function normalizeHistoryItem(raw: unknown): HistoryItem | null {
  const item = raw as Partial<HistoryItem> | null;
  if (!item || typeof item !== 'object') return null;
  if (!item.id || !isGame(item.game)) return null;
  const result = String(item.result || '').trim();
  if (!result) return null;
  return {
    id: String(item.id),
    game: item.game,
    label: String(item.label || gameInfo(item.game).name),
    result,
    time: String(item.time || ''),
    tick: Number.isFinite(Number(item.tick)) ? Number(item.tick) : undefined,
  };
}

function historyOrderValue(item: HistoryItem) {
  if (typeof item.tick === 'number') return item.tick;
  const numeric = Number(String(item.id).split('_')[0]);
  return Number.isFinite(numeric) ? numeric : 0;
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
      history: Array.isArray(raw.history) ? dedupeHistoryByGame(raw.history.map(normalizeHistoryItem).filter((item): item is HistoryItem => Boolean(item))) : fallback.history,
    };
  } catch {
    return fallback;
  }
}

function dedupeHistoryByGame(items: HistoryItem[]) {
  const byGame = new Map<GameId, HistoryItem>();
  for (const item of items) {
    const current = byGame.get(item.game);
    if (!current || historyOrderValue(item) >= historyOrderValue(current)) {
      byGame.set(item.game, item);
    }
  }
  return Array.from(byGame.values())
    .sort((a, b) => historyOrderValue(b) - historyOrderValue(a))
    .slice(0, MAX_HISTORY);
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
