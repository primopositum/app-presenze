import { apiBase, authFetch } from '$lib/api';

const BASE = apiBase();

type Opts = RequestInit & { json?: any };

async function request(path: string, opts: Opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const res = await authFetch(url, opts);

  let data: any = null;
  const contentType = res.headers.get('content-type');
  if (res.status !== 204 && res.status !== 205) {
    data = contentType?.includes('application/json') ? JSON.parse((await res.text()) || 'null') : await res.text();
  }

  if (!res.ok) {
    const message = (data?.errors || data?.error || data?.detail) || res.statusText || 'Request failed';
    throw new Error(message);
  }

  return data;
}

export type Automobile = {
  id?: number;
  a_id?: number;
  A_ID?: number;
  marca: string;
  alimentazione: string;
  descrizione: string;
  is_active: boolean;
  coefficiente: number | string;
  data_creaz: string;
  data_upd: string;
};

export type AutomobileCreate = Pick<
  Automobile,
  'marca' | 'alimentazione' | 'descrizione' | 'is_active' | 'coefficiente'
>;

export type AutomobileUpdate = Partial<AutomobileCreate>;

export type AutomobilePatch = {
  coefficiente?: number | string;
  is_active?: boolean;
};

export type AutomobileListParams = {
  is_active?: boolean;
};

export type AutomobileDeleteResponse = {
  detail: string;
  action: 'archived' | 'deleted';
  data?: Automobile;
};

export type AutoPdfCurrentMonthItem = {
  auto_id?: number | string;
  filename?: string;
  path?: string;
  url?: string;
  mese_anno?: string;
  created_at?: string | number;
  [key: string]: any;
};

export function getAutomobili(params: AutomobileListParams = {}) {
  const qs = new URLSearchParams();
  if (params.is_active !== undefined) qs.set('is_active', String(params.is_active));
  const tail = qs.toString();
  return request(`/automobili/${tail ? `?${tail}` : ''}`) as Promise<Automobile[]>;
}

export function createAutomobile(payload: AutomobileCreate) {
  return request('/automobili/', { method: 'POST', json: payload }) as Promise<Automobile>;
}

export function getAutomobileDetail(pk: number | string) {
  return request(`/automobili/${pk}/`) as Promise<Automobile>;
}

export function updateAutomobile(pk: number | string, payload: AutomobileUpdate) {
  return request(`/automobili/${pk}/`, { method: 'PUT', json: payload }) as Promise<Automobile>;
}

export function patchAutomobile(pk: number | string, payload: AutomobilePatch) {
  return request(`/automobili/${pk}/patch/`, { method: 'PATCH', json: payload }) as Promise<Automobile>;
}

export function updateAutomobileCoeff(pk: number | string, coefficiente: number | string) {
  return patchAutomobile(pk, { coefficiente });
}

export function updateAutomobileIsActive(pk: number | string, is_active: boolean) {
  return patchAutomobile(pk, { is_active });
}

export function deleteAutomobile(pk: number | string) {
  return request(`/automobili/${pk}/delete/`, { method: 'DELETE' }) as Promise<AutomobileDeleteResponse>;
}

export function uploadPDFauto(auto_id: number | string, file: File, mese_anno?: string) {
  const form = new FormData();
  form.append('file', file);
  if (mese_anno) form.append('mese_anno', mese_anno);
  return request(`/automobili/${auto_id}/PDFauto/`, { method: 'POST', body: form }) as Promise<any>;
}

export function deletePDFauto(auto_id: number | string, mese_anno?: string) {
  const qs = new URLSearchParams();
  if (mese_anno) qs.set('mese_anno', mese_anno);
  const tail = qs.toString();
  return request(`/automobili/${auto_id}/PDFauto/delete/${tail ? `?${tail}` : ''}`, {
    method: 'DELETE',
  }) as Promise<any>;
}

export function getPDFautoCurrentMonthList(data?: string) {
  const qs = new URLSearchParams();
  if (data) qs.set('data', data);
  const tail = qs.toString();
  return request(`/automobili/PDFauto/by-date/${tail ? `?${tail}` : ''}`) as Promise<AutoPdfCurrentMonthItem[]>;
}
