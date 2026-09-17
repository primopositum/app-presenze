import {
  clientiList,
  clienteCreate,
  clienteDelete,
  clienteUpdate,
  contrattiClientiList,
  contrattoClienteCreate,
  contrattoClienteDelete,
  contrattoClientePoolTaskAppend,
  contrattoClientePoolTaskDelete,
  contrattoClienteUpdate,
  type ClientePayload,
  type ContrattoClienteCreatePayload,
  type ContrattoClienteUpdatePayload
} from '$lib/services/clienti';

export const useClientiList = clientiList;
export const useClienteCreate = clienteCreate;
export const useClienteUpdate = clienteUpdate;
export const useClienteDelete = clienteDelete;

export const useContrattiClientiList = contrattiClientiList;
export const useContrattoClienteCreate = contrattoClienteCreate;
export const useContrattoClienteUpdate = contrattoClienteUpdate;
export const useContrattoClienteDelete = contrattoClienteDelete;

export async function useContrattoClientePoolTaskAppend(id: number, task: string) {
  const normalizedTask = task.trim().toUpperCase();
  if (!normalizedTask) throw new Error('Task obbligatoria');
  return contrattoClientePoolTaskAppend(id, normalizedTask);
}

export async function useContrattoClientePoolTaskDelete(id: number, task: string) {
  const normalizedTask = task.trim();
  if (!normalizedTask) throw new Error('Task obbligatoria');
  return contrattoClientePoolTaskDelete(id, normalizedTask);
}

export type { ClientePayload, ContrattoClienteCreatePayload, ContrattoClienteUpdatePayload };
