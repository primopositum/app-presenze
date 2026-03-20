import {
  updateTimeEntryValidation,
  createTimeEntry,
  updateTimeEntry,
  deleteTimeEntry,
  getMeseScorsoPdf,
  type BulkValidationUpdate,
  type TimeEntry,
  type TimeEntryCreate,
  type TimeEntryUpdate
} from '$lib/services/timeEntries';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';
import { refreshProfileUser } from '$lib/services/users';
export type SubmitHoursPayload = {
  date: string;   // YYYY-MM-DD
  hours: number;  // ore da inserire
  note?: string;
  type: number;
};



/**
 * @param utenteId 
 * @param type 
 * @param validationLevel 
 */
export function useSubmitHours(params: {
  utenteId: number;
  validationLevel?: number;
}) {
  return async (payload: SubmitHoursPayload): Promise<{ ok: true; payload: TimeEntry }> => {
    const entry: TimeEntryCreate = {
      utente_id: params.utenteId,
      data: payload.date,
      type: payload.type,
      ore_tot: payload.hours,
      note: payload.note ?? '',
      ...(params.validationLevel !== undefined ? { validation_level: params.validationLevel } : {})
    };
    const created = (await createTimeEntry(entry)) as TimeEntry;
    await refreshProfileUser();

    return { ok: true, payload: created };
  };
}

export function useUpdateHours(params: {
  utenteId: number,
  TimeEntryId: number,
}){
  return async (payload: SubmitHoursPayload): Promise<{ ok: true; payload: TimeEntry }> => {
    const entry: TimeEntryUpdate = {
      utente_id: params.utenteId,
      data: payload.date,
      type: payload.type,
      ore_tot: payload.hours,
      note: payload.note ?? ''
    };
    const updated = (await updateTimeEntry(params.TimeEntryId ,entry)) as TimeEntry;
    await refreshProfileUser();

    return { ok: true, payload: updated };
  };
}
export function useDeleteHours(params: { TimeEntryId: number }){
  return async (): Promise<{ ok: true; payload: TimeEntry }> => {
    const deleted = (await deleteTimeEntry(params.TimeEntryId)) as TimeEntry;
    await refreshProfileUser();

    return { ok: true, payload: deleted };
  };
}


export function useUpdateValidationLevel(params: {
  date: string;
  u_id?: number;
}) {
  return async (): Promise<{ ok: true; payload: any }> => {
    const isSuperuser = !!get(auth)?.user?.is_superuser;
    const entry: BulkValidationUpdate = {
      data: params.date,
      ...(isSuperuser && params.u_id !== undefined ? { utente_id: params.u_id } : {})
    };
    const updated = await updateTimeEntryValidation(entry);

    return { ok: true, payload: updated };
  };
}

export function useGeneratePDF(params: {
  date: string;
  u_id?: number;
  note?: string;
}) {
  return async (): Promise<{ ok: true; payload: Blob }> => {
    const pdf = await getMeseScorsoPdf({ date: params.date, u_id: params.u_id, note: params.note });
    return { ok: true, payload: pdf };
  };
}
