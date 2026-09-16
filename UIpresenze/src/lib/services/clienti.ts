import { apiBase, authFetch } from '$lib/api';

const BASE = apiBase();

export type Cliente = {
  id: number;
  nome: string;
  indirizzo: string;
  telefono: string;
};

export type ClientePayload = Omit<Cliente, 'id'>;

export type ContrattoCliente = {
  id: number;
  contract_id: string;
  client?: Cliente;
  client_id: number;
  value: string;
  current_value?: string;
  pool_task: string[];
  start_date: string;
  end_date: string | null;
  periodicity: Periodicity | null;
  created_at: string;
  updated_at: string;
};

export type Periodicity = {
  periodic_value: string;
  period_days: number;
  first_meeting_date: string;
  notification_days: number;
};

export type PeriodicityPayload = {
  periodic_value: string | number;
  period_days: number;
  first_meeting_date: string;
  notification_days: number;
};

export type ContrattoClienteCreatePayload = {
  contract_id: string;
  client_id: number;
  value: string | number;
  pool_task?: string[];
  start_date: string;
  end_date: string;
  periodicity?: PeriodicityPayload | null;
};

export type ContrattoClienteUpdatePayload = Partial<
  Pick<ContrattoClienteCreatePayload, 'contract_id' | 'client_id' | 'value' | 'pool_task' | 'start_date' | 'end_date'>
>;

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

async function request<T>(path: string, method: HttpMethod, json?: Record<string, unknown>): Promise<T> {
  const headers = new Headers();
  if (json !== undefined) headers.set('Content-Type', 'application/json');

  const response = await authFetch(
    `${BASE}${path}`,
    {
      method,
      headers,
      body: json === undefined ? undefined : JSON.stringify(json)
    },
    true
  );

  if (response.status === 204) return undefined as T;

  const isJson = response.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await response.json() : await response.text();
  if (!response.ok) {
    const message = (isJson && (data?.detail || data?.error || data?.task?.[0])) || response.statusText;
    throw new Error(message || 'Richiesta non riuscita');
  }
  return data as T;
}

export function clientiList() {
  return request<Cliente[]>('/clienti/', 'GET');
}

export function clienteCreate(payload: ClientePayload) {
  return request<Cliente>('/clienti/', 'POST', payload);
}

export function clienteUpdate(id: number, payload: ClientePayload) {
  return request<Cliente>(`/clienti/${id}/`, 'PATCH', payload);
}

export function clienteDelete(id: number) {
  return request<void>(`/clienti/${id}/`, 'DELETE');
}

export function contrattiClientiList() {
  return request<ContrattoCliente[]>('/contratti-clienti/', 'GET');
}

export function contrattoClienteCreate(payload: ContrattoClienteCreatePayload) {
  return request<ContrattoCliente>('/contratti-clienti/', 'POST', payload);
}

export function contrattoClienteUpdate(id: number, payload: ContrattoClienteUpdatePayload) {
  return request<ContrattoCliente>(`/contratti-clienti/${id}/`, 'PATCH', payload);
}

export function contrattoClienteDelete(id: number) {
  return request<void>(`/contratti-clienti/${id}/`, 'DELETE');
}

export function contrattoClientePoolTaskAppend(id: number, task: string) {
  return request<ContrattoCliente>(`/contratti-clienti/${id}/pool-task/`, 'POST', { task });
}

export function contrattoClientePoolTaskDelete(id: number, task: string) {
  return request<ContrattoCliente>(`/contratti-clienti/${id}/pool-task/`, 'DELETE', { task });
}
