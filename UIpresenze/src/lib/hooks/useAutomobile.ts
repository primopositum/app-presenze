import {
  createAutomobile,
  deleteAutomobile,
  getAutomobileDetail,
  getAutomobili,
  patchAutomobile,
  type Automobile,
  type AutomobileCreate,
  type AutomobileDeleteResponse,
  type AutomobileListParams,
  type AutomobilePatch,
  type AutomobileUpdate,
  updateAutomobile,
  updateAutomobileCoeff,
  updateAutomobileIsActive
} from '$lib/services/automobili';

export function useAutomobiliList(params: AutomobileListParams = {}) {
  return async (): Promise<{ ok: true; payload: Automobile[] }> => {
    const list = await getAutomobili(params);
    return { ok: true, payload: list };
  };
}

export function useAutomobileDetail(params: { pk: number | string }) {
  return async (): Promise<{ ok: true; payload: Automobile }> => {
    const detail = await getAutomobileDetail(params.pk);
    return { ok: true, payload: detail };
  };
}

export function useCreateAutomobile() {
  return async (payload: AutomobileCreate): Promise<{ ok: true; payload: Automobile }> => {
    const created = await createAutomobile(payload);
    return { ok: true, payload: created };
  };
}

export function useUpdateAutomobile(params: { pk: number | string }) {
  return async (payload: AutomobileUpdate): Promise<{ ok: true; payload: Automobile }> => {
    const updated = await updateAutomobile(params.pk, payload);
    return { ok: true, payload: updated };
  };
}

export function usePatchAutomobile(params: { pk: number | string }) {
  return async (payload: AutomobilePatch): Promise<{ ok: true; payload: Automobile }> => {
    const updated = await patchAutomobile(params.pk, payload);
    return { ok: true, payload: updated };
  };
}

export function useUpdateAutomobileCoeff(params: { pk: number | string }) {
  return async (coefficiente: number | string): Promise<{ ok: true; payload: Automobile }> => {
    const updated = await updateAutomobileCoeff(params.pk, coefficiente);
    return { ok: true, payload: updated };
  };
}

export function useUpdateAutomobileIsActive(params: { pk: number | string }) {
  return async (is_active: boolean): Promise<{ ok: true; payload: Automobile }> => {
    const updated = await updateAutomobileIsActive(params.pk, is_active);
    return { ok: true, payload: updated };
  };
}

export function useDeleteAutomobile(params: { pk: number | string }) {
  return async (): Promise<{ ok: true; payload: AutomobileDeleteResponse }> => {
    const deleted = await deleteAutomobile(params.pk);
    return { ok: true, payload: deleted };
  };
}