import { writable } from 'svelte/store';

export type HourBalanceExtra = {
  title: string;
  saldo: number;
  color?: [string, string];
};

export const hourBalanceExtra = writable<HourBalanceExtra | null>(null);
