import { auth } from '$lib/stores/auth';
import { get } from 'svelte/store';
import {
  createSignature,
  getLatestSignature,
  normalizeSignaturePayload,
  type Signature,
  type SignaturePayload
} from '$lib/services/signatures';

async function waitForToken(timeoutMs = 3000) {
  const existing = get(auth).token;
  if (existing) return existing;
  return new Promise<string | null>((resolve) => {
    const timer = setTimeout(() => {
      unsub();
      resolve(null);
    }, timeoutMs);
    const unsub = auth.subscribe((value) => {
      if (value.token) {
        clearTimeout(timer);
        unsub();
        resolve(value.token);
      }
    });
  });
}

export async function useCreateSignatureApi(payload: SignaturePayload): Promise<{
  signature: Signature | null;
  error: string | null;
}> {
  try {
    const token = await waitForToken();
    if (!token) throw new Error('Token non disponibile');

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
    const token = await waitForToken();
    if (!token) throw new Error('Token non disponibile');

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
