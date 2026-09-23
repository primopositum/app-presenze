/**
 * Store condiviso NON persistente dei dati usati dai grafici (`$lib/components/charts`).
 *
 * Vive solo in memoria: nessun localStorage/sessionStorage, al reload riparte vuoto.
 * Serve a far leggere gli stessi dati a piu' componenti senza passarli di prop in prop:
 * - la pagina /JiraHistory scrive issue, worklog, task e selezione dei progetti;
 * - ClientiSection e le schermate contratti condividono clienti e contratti commerciali.
 */
import { get, writable } from 'svelte/store';
import {
  clientiList,
  contrattiClientiList,
  type Cliente,
  type ContrattoCliente
} from '$lib/services/clienti';
import type { JiraHistoryIssue } from '$lib/services/jira';

export type ChartPoolTask = {
  key: string;
  summary: string;
  seconds: number;
};

/** Una singola registrazione di ore, con la data in cui e' stata loggata. */
export type ChartWorklogEntry = {
  /** YYYY-MM-DD. */
  date: string;
  seconds: number;
  author: string;
  projectKey: string;
  issueKey: string;
};

export type ChartsDataState = {
  /** Issue Jira (gia' appiattite) del periodo selezionato. */
  issues: JiraHistoryIssue[];
  /** Task Jira con le ore totali del periodo, usate per il pool dei contratti. */
  poolTasks: ChartPoolTask[];
  /** Worklog del periodo: servono ai grafici con un asse temporale. */
  worklogEntries: ChartWorklogEntry[];
  /** Progetti selezionati nella barra di sinistra: vuoto = nessun filtro. */
  selectedProjectKeys: string[];
  jiraLoading: boolean;
  jiraError: string;
  clienti: Cliente[];
  contratti: ContrattoCliente[];
  contrattiLoaded: boolean;
  /** Prima carica: non c'e' ancora niente da mostrare. */
  contrattiLoading: boolean;
  /** Ricarica con i dati gia' a schermo: si tiene la vista, non si svuota. */
  contrattiRefreshing: boolean;
  contrattiError: string;
};

const initialState: ChartsDataState = {
  issues: [],
  poolTasks: [],
  worklogEntries: [],
  selectedProjectKeys: [],
  jiraLoading: false,
  jiraError: '',
  clienti: [],
  contratti: [],
  contrattiLoaded: false,
  contrattiLoading: false,
  contrattiRefreshing: false,
  contrattiError: ''
};

const store = writable<ChartsDataState>({ ...initialState });

export const chartsData = { subscribe: store.subscribe };

let contrattiInFlight: Promise<void> | null = null;

function patch(changes: Partial<ChartsDataState>) {
  store.update((state) => ({ ...state, ...changes }));
}

export function setChartIssues(issues: JiraHistoryIssue[]) {
  patch({ issues: issues || [] });
}

export function setChartPoolTasks(poolTasks: ChartPoolTask[]) {
  patch({ poolTasks: poolTasks || [] });
}

export function setChartWorklogEntries(worklogEntries: ChartWorklogEntry[]) {
  patch({ worklogEntries: worklogEntries || [] });
}

export function setChartSelectedProjectKeys(selectedProjectKeys: string[]) {
  patch({ selectedProjectKeys: selectedProjectKeys || [] });
}

export function setChartJiraStatus(jiraLoading: boolean, jiraError = '') {
  patch({ jiraLoading, jiraError });
}

/** Sostituisce un contratto gia' in memoria (append/delete di una task del pool). */
export function replaceContratto(updated: ContrattoCliente) {
  store.update((state) => ({
    ...state,
    contratti: state.contratti.map((contratto) =>
      contratto.id === updated.id ? updated : contratto
    )
  }));
}

/**
 * Toglie subito un contratto dalla memoria condivisa.
 * Si chiama appena il server conferma l'eliminazione: senza, l'unico modo di
 * aggiornare la vista sarebbe una ricarica completa, che svuota la pagina
 * per il tempo della richiesta.
 */
export function removeContratto(id: number) {
  store.update((state) => ({
    ...state,
    contratti: state.contratti.filter((contratto) => contratto.id !== id)
  }));
}

/** Toglie un cliente e i contratti che gli appartenevano. */
export function removeCliente(id: number) {
  store.update((state) => ({
    ...state,
    clienti: state.clienti.filter((cliente) => cliente.id !== id),
    contratti: state.contratti.filter((contratto) => contratto.client_id !== id)
  }));
}

/**
 * Carica clienti e contratti una sola volta per sessione.
 * Le chiamate concorrenti condividono la stessa richiesta; `force` ricarica davvero.
 *
 * Durante una ricarica i dati precedenti restano nello store: chi legge distingue
 * la prima carica (`contrattiLoading`) dall'aggiornamento (`contrattiRefreshing`)
 * e non sostituisce mai il contenuto con uno scheletro.
 */
export async function ensureContrattiLoaded(force = false): Promise<void> {
  const current = get(store);
  if (!force && current.contrattiLoaded) return;
  if (!force && contrattiInFlight) return contrattiInFlight;

  const firstLoad = !current.contrattiLoaded;
  patch({
    contrattiLoading: firstLoad,
    contrattiRefreshing: !firstLoad,
    contrattiError: ''
  });

  contrattiInFlight = (async () => {
    try {
      const [clienti, contratti] = await Promise.all([clientiList(), contrattiClientiList()]);
      patch({
        clienti,
        contratti,
        contrattiLoaded: true,
        contrattiLoading: false,
        contrattiRefreshing: false,
        contrattiError: ''
      });
    } catch (cause) {
      patch({
        contrattiLoaded: true,
        contrattiLoading: false,
        contrattiRefreshing: false,
        contrattiError:
          cause instanceof Error ? cause.message : 'Impossibile caricare clienti e contratti.'
      });
      throw cause;
    } finally {
      contrattiInFlight = null;
    }
  })();

  return contrattiInFlight;
}

export function resetChartsData() {
  contrattiInFlight = null;
  store.set({ ...initialState });
}
