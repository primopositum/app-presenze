import {
  createTimeEntryRangeOverride,
  type TimeEntryRangeOverrideCreate
} from '$lib/services/timeEntries';
import { refreshProfileUser } from '$lib/services/users';

export type TimeEntryRangeOverrideInput = {
  utenteId: number;
  dataS: string;
  dataE: string;
  type: number;
};

function normalizeIsoDate(value: string) {
  return String(value ?? '').trim().slice(0, 10);
}

function normalizeRangeOverridePayload(input: TimeEntryRangeOverrideInput): TimeEntryRangeOverrideCreate {
  const utente_id = Number(input.utenteId);
  const type = Number(input.type);
  const dataS = normalizeIsoDate(input.dataS);
  const dataE = normalizeIsoDate(input.dataE);

  if (!Number.isInteger(utente_id) || utente_id <= 0) {
    throw new Error('Utente non valido');
  }
  if (!dataS || !dataE) {
    throw new Error('Date range obbligatorie');
  }
  if (!Number.isInteger(type) || type <= 0) {
    throw new Error('Tipo non valido');
  }
  if (new Date(dataS).getTime() > new Date(dataE).getTime()) {
    throw new Error('Intervallo date non valido');
  }

  return { utente_id, dataS, dataE, type };
}

export function useRangeOverrideTimeEntries() {
  return async (input: TimeEntryRangeOverrideInput): Promise<{ ok: true; payload: any }> => {
    const payload = normalizeRangeOverridePayload(input);
    const created = await createTimeEntryRangeOverride(payload);
    await refreshProfileUser();
    return { ok: true, payload: created };
  };
}

