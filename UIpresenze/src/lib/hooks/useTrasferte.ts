import {
  createTrasferta,
  type TrasfertaCreate,
  type Trasferta,
  deleteTrasferta,
  createSpesa,
  deleteSpesa,
  type SpesaCreate,
  type Spesa,
  getScontriniByTrasferta,
  getScontrinoByTrasferta,
  type ScontrinoFile,
  type ScontrinoUploadResponse,
  uploadScontrinoByTrasferta,
  deleteScontrinoByTrasferta,
  validateTrasferta
} from '$lib/services/trasferte';
import { getPDFautoCurrentMonthList, uploadPDFauto, type AutoPdfCurrentMonthItem } from '$lib/services/automobili';
import { refreshProfileUser } from '$lib/services/users';



export function useCreateTrasferta(params: { utente_mail?: string }) {
  return async (payload: TrasfertaCreate): Promise<{ ok: true; payload: Trasferta }> => {
    const entry: TrasfertaCreate = {
      ...payload,
      ...(params.utente_mail !== undefined ? { utente_email: params.utente_mail } : {})
    };
    const created = (await createTrasferta(entry)) as Trasferta;
    return { ok: true, payload: created };
  };
}

export function useDeleteTrasferta(params: { tId: string }) {
  return async (): Promise<{ ok: true; payload: { message?: string } }> => {
   const deleted = await deleteTrasferta(params.tId);
       await refreshProfileUser();
   
       return { ok: true, payload: deleted };
     };
  }

export function useCreateSpese(params: { tId: string | number }) {
  return {
    addSpesa: async (payload: SpesaCreate): Promise<{ ok: true; payload: Spesa }> => {
      const created = await createSpesa(params.tId, payload);
      return { ok: true, payload: created };
    }
  };
}

export function useDeleteSpese(params: { sId: string | number }) {
  return async (): Promise<{ ok: true; payload: { message?: string } }> => {
    const deleted = await deleteSpesa(params.sId);
    return { ok: true, payload: deleted };
  };
}

export function useScontrini(params: { tId: string | number }) {
  return {
    listScontrini: async (): Promise<{ ok: true; payload: ScontrinoFile[] }> => {
      const list = await getScontriniByTrasferta(params.tId);
      return { ok: true, payload: list };
    },
    getScontrino: async (filename: string): Promise<{ ok: true; payload: Blob }> => {
      const file = await getScontrinoByTrasferta(params.tId, filename);
      return { ok: true, payload: file };
    },
    deleteScontrino: async (filename: string): Promise<{ ok: true; payload: { message?: string } }> => {
      const deleted = await deleteScontrinoByTrasferta(params.tId, filename);
      return { ok: true, payload: deleted };
    },
    uploadScontrino: async (file: File): Promise<{ ok: true; payload: ScontrinoUploadResponse }> => {
      const created = await uploadScontrinoByTrasferta(params.tId, file);
      return { ok: true, payload: created };
    }
  };
}

export function useUploadPdfAuto(params: { auto_id: string | number }) {
  return async (
    file: File,
    mese_anno?: string
  ): Promise<{ ok: true; payload: any }> => {
    const uploaded = await uploadPDFauto(params.auto_id, file, mese_anno);
    return { ok: true, payload: uploaded };
  };
}

export function usePdfAutoCurrentMonthList() {
  return async (): Promise<{ ok: true; payload: AutoPdfCurrentMonthItem[] }> => {
    const list = await getPDFautoCurrentMonthList();
    return { ok: true, payload: list };
  };
}
export function useValidateTrasferta(params: { tId: string | number }) {
  return async (): Promise<{ ok: true; payload: Trasferta }> => {
    const validated = await validateTrasferta(params.tId);
    return { ok: true, payload: validated };
  };
}
