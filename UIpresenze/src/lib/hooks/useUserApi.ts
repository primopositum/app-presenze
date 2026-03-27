import type { User } from '$lib/services/users';
import { deleteAccountById, fetchUsers, fetchProfiles, normalizeUsersPayload, updateAccount } from '$lib/services/users';
import { auth } from '$lib/stores/auth';
import { get } from 'svelte/store';
import { timeEntryUser } from '$lib/stores/timeEntryUser';
import type { UpdateAccountPayload } from '$lib/services/users';


export async function useUsersApi(): Promise<{
  users: User[];
  error: string | null;
}> {
  try {
    const data = await fetchUsers();
    const users = normalizeUsersPayload(data);
    return { users, error: null };
  } catch (e) {
    return {
      users: [],
      error: (e as Error).message ?? 'Errore caricando utenti'
    };
  }
}


export async function useOneUserApi(uId?: number){
  let users: User[] = [];
  let error: string | null = null;
  if (!uId) {
    return;
  }
  try {
    const result = await useUsersApi();
    users = result.users;
    error = result.error;
  } catch (e) {
    error = 'Impossibile caricare gli utenti';
    console.error(e);
  }
  if (error) return;
  const user = users.find((u) => u.id === uId);
  if (user) {
    timeEntryUser.setUser(user);
  }
  // return user
}


export async function useUserProfile(): Promise<{
  users: User[];
  error: string | null;
}> {
  try {
    const data = await fetchProfiles();
    const users = normalizeUsersPayload(data);
    return { users, error: null };
  } catch (e) {
    return {
      users: [],
      error: (e as Error).message ?? 'Errore caricando profili'
    };
  }
}

export async function useUpdateAccountApi(payload: UpdateAccountPayload): Promise<{
  user: User | null;
  error: string | null;
}> {
  try {
    const authUser = get(auth).user;
    if (!authUser?.id) {
      throw new Error('Utente autenticato non disponibile');
    }
    const isAdmin = authUser?.is_superuser === true || authUser?.is_staff === true;
    const requestedTargetId = Number(payload.id ?? payload.user_id ?? authUser.id);
    if (!Number.isFinite(requestedTargetId)) {
      throw new Error('ID utente non valido');
    }
    if (!isAdmin && requestedTargetId !== Number(authUser.id)) {
      throw new Error('Un utente non admin può modificare solo il proprio profilo');
    }

    const normalizedPayload: UpdateAccountPayload = {
      ...payload,
      id: requestedTargetId,
      user_id: requestedTargetId
    };

    const data = await updateAccount(normalizedPayload);
    const user = normalizeUsersPayload(data)[0] ?? null;
    if (!user) {
      throw new Error('Risposta profilo non valida');
    }
    const expectedTargetId = normalizedPayload.id ?? normalizedPayload.user_id;
    if (expectedTargetId !== undefined && Number(expectedTargetId) !== user.id) {
      throw new Error(`Risposta incoerente: atteso utente ${expectedTargetId}, ricevuto ${user.id}`);
    }

    if (authUser?.id === user.id) {
      auth.setUser(user);
      const teUser = get(timeEntryUser).user;
      if (teUser?.id === user.id) {
        timeEntryUser.setUser(user);
      }
    }

    return { user, error: null };
  } catch (e) {
    return {
      user: null,
      error: (e as Error).message ?? 'Errore aggiornando account'
    };
  }
}

export async function useDeleteAccountApi(userId: number): Promise<{
  deletedUserId: number | null;
  error: string | null;
}> {
  try {
    const authUser = get(auth).user;
    if (!authUser?.is_superuser) {
      throw new Error('Solo i superuser possono eliminare account');
    }

    const targetUserId = Number(userId);
    if (!Number.isFinite(targetUserId)) {
      throw new Error('ID utente non valido');
    }

    const data = await deleteAccountById(targetUserId);
    const deletedUserId = Number(data?.deleted_user_id);
    if (!Number.isFinite(deletedUserId)) {
      throw new Error('Risposta delete account non valida');
    }
    return { deletedUserId, error: null };
  } catch (e) {
    return {
      deletedUserId: null,
      error: (e as Error).message ?? 'Errore eliminando account'
    };
  }
}
