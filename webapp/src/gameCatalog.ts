import type { GameId } from './types';

export type GameIconKey = 'coin' | 'dice' | 'rps' | 'roulette' | 'wheel';

export type GameInfo = {
  id: GameId;
  name: string;
  subtitle: string;
  iconKey: GameIconKey;
  accent: string;
};

export const GAME_CATALOG: GameInfo[] = [
  {
    id: 'COIN',
    name: 'Flip Coin',
    subtitle: 'Heads or tails',
    iconKey: 'coin',
    accent: '#f7b733',
  },
  {
    id: 'DICE',
    name: 'Roll Dice',
    subtitle: 'Classic random roll',
    iconKey: 'dice',
    accent: '#2f80ff',
  },
  {
    id: 'RPS',
    name: 'RPS',
    subtitle: 'Rock paper scissors',
    iconKey: 'rps',
    accent: '#8a63d2',
  },
  {
    id: 'ROULETTE',
    name: 'Russian Roulette',
    subtitle: 'Six rounds of suspense',
    iconKey: 'roulette',
    accent: '#e0362f',
  },
  {
    id: 'WHEEL',
    name: 'Decision Wheel',
    subtitle: 'Custom options',
    iconKey: 'wheel',
    accent: '#22a06b',
  },
];

export function gameInfo(id: GameId) {
  return GAME_CATALOG.find((game) => game.id === id) || GAME_CATALOG[0];
}
