import { writable } from 'svelte/store';

export type HourBalanceExtra = {
  title: string;
  saldo: number;
  color?: [string, string];
  saldoCumulativoMensile?: number[];
  year?: number;
  month?: number;
};

export const hourBalanceExtra = writable<HourBalanceExtra | null>(null);
