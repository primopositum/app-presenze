import {
  getSaldoByUserId,
  patchSaldoByUserId,
  type Saldo,
  type SaldoPatchPayload,
  type SaldoRecord
} from '$lib/services/saldo';

export async function useSaldoApi(userId?: number): Promise<{
  saldo: Saldo | null;
  records: SaldoRecord[];
  error: string | null;
}> {
  if (!userId) {
    return { saldo: null, records: [], error: 'Utente non disponibile' };
  }

  try {
    const saldo = await getSaldoByUserId(userId);
    return { saldo, records: saldo.saldo ?? [], error: null };
  } catch (e) {
    return {
      saldo: null,
      records: [],
      error: (e as Error).message ?? 'Errore caricando saldo'
    };
  }
}

export async function usePatchSaldoApi(userId: number, payload: SaldoPatchPayload): Promise<{
  saldo: Saldo | null;
  records: SaldoRecord[];
  error: string | null;
}> {
  try {
    const saldo = await patchSaldoByUserId(userId, payload);
    return { saldo, records: saldo.saldo ?? [], error: null };
  } catch (e) {
    return {
      saldo: null,
      records: [],
      error: (e as Error).message ?? 'Errore aggiornando saldo'
    };
  }
}
