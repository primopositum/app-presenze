import {
  createSignature,
  getLatestSignature,
  normalizeSignaturePayload,
  type Signature,
  type SignaturePayload
} from '$lib/services/signatures';

export async function useCreateSignatureApi(payload: SignaturePayload): Promise<{
  signature: Signature | null;
  error: string | null;
}> {
  try {
    const data = await createSignature(payload);
    const signature = normalizeSignaturePayload(data);
    if (!signature) throw new Error('Risposta firma non valida');
    return { signature, error: null };
  } catch (e) {
    return {
      signature: null,
      error: (e as Error).message ?? 'Errore salvataggio firma'
    };
  }
}

export async function useLatestSignatureApi(userId?: number): Promise<{
  signature: Signature | null;
  error: string | null;
}> {
  try {
    const data = await getLatestSignature(userId);
    const signature = normalizeSignaturePayload(data);
    return { signature, error: null };
  } catch (e) {
    return {
      signature: null,
      error: (e as Error).message ?? 'Errore caricamento firma'
    };
  }
}
