export type GameId = 'COIN' | 'DICE' | 'RPS' | 'ROULETTE' | 'WHEEL';

export type DeviceInfo = {
  name?: string;
  talId?: string;
  slot?: string | number;
  slotId?: string;
  deviceId?: string;
  online?: boolean;
  raw?: unknown;
};

export type AppStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'installing'
  | 'connecting'
  | 'connected'
  | 'syncing'
  | 'error';

export type HistoryItem = {
  id: string;
  game: GameId;
  label: string;
  time: string;
};
