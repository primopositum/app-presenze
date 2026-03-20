import {
  type ContrattoCreate,
  updateContrattoOre,
  createContratto,
  resolveUId
} from '$lib/services/contratti';

export function useUpdateContrattoOre(params: { u_id?: number }) {
  return async (ore_sett: Array<number | string>): Promise<{ ok: true; payload: any }> => {
    const uId = resolveUId(params.u_id);
    if (uId === undefined) {
      throw new Error('u_id è obbligatorio per aggiornare un contratto');
    }
    const updated = await updateContrattoOre(uId, ore_sett);
    return { ok: true, payload: updated };
  };
}

export function useCreateContratto(params: { u_id?: number }) {
  return async (contratto: ContrattoCreate): Promise<{ ok: true; payload: any }> => {
    const uId = resolveUId(params.u_id);
    if (uId === undefined) {
      throw new Error('u_id è obbligatorio per creare un contratto');
    }
    const created = await createContratto(uId, contratto);
    return { ok: true, payload: created };
  };
}

// Back-compat for typo in older imports
export const useCceateContratto = useCreateContratto;
