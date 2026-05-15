<script lang="ts">
  import { goto } from '$app/navigation';
  import JiraCompletedBar from '$lib/components/Jira/JiraCompletedBar.svelte';
  import JiraHistoryCharts from '$lib/components/Jira/JiraHistoryCharts.svelte';

  type JiraIssue = {
    key: string;
    fields?: {
      project?: { key?: string; name?: string };
      timespent?: number | null;
      aggregatetimespent?: number | null;
      timeestimate?: number | null;
      aggregatetimeestimate?: number | null;
      timeoriginalestimate?: number | null;
      aggregatetimeoriginalestimate?: number | null;
      timetracking?: {
        timeSpentSeconds?: number;
        originalEstimateSeconds?: number;
      } | null;
    };
  };

  let selectedProjectKeys: string[] = [];
  let searchQuery = '';
  let completedIssues: JiraIssue[] = [];
</script>

<main class="history-page">
  <button
    class="back-arrow-btn"
    type="button"
    on:click={() => goto('/business')}
    aria-label="Torna alla pagina business"
    title="Torna alla pagina business"
  >
    ←
  </button>
  <h1 class="page-title">Jira History</h1>
  <header class="page-header">
    <div class="header-main">
      <div>
        <p>Analisi ore su progetti completati e distribuzione in base ai progetti selezionati.</p>
      </div>
      <div class="search-wrap">
        <span class="search-ico">/</span>
        <input
          type="text"
          class="search-input"
          bind:value={searchQuery}
          placeholder="Cerca progetto (chiave o nome)..."
        />
      </div>
    </div>
  </header>

  <section class="layout-row">
    <div class="left-pane">
      <JiraCompletedBar bind:issuesData={completedIssues} bind:selectedProjectKeys {searchQuery} />
    </div>

    <aside class="right-pane">
      <JiraHistoryCharts issues={completedIssues} {selectedProjectKeys} />
    </aside>
  </section>
</main>

<style>
  .history-page {
    max-width: 1456px;
    margin: 0 auto;
    padding: 1.25rem 0 2.4rem;
  }
  .page-title {
    margin: 0 0 0.7rem;
    font-size: 2.21rem;
    line-height: 1.05;
    color: #0f172a;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    font-family: var(--font-infinity);
  }

  .page-header {
    margin-bottom: 0.9rem;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.85rem 1rem;
    background: #ffffff;
  }
  .header-main {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.9rem;
  }

  .page-header p {
    margin: 0;
    color: #475569;
    font-size: 0.82rem;
    font-family: var(--font-mono);
  }
  .search-wrap {
    min-width: 320px;
    width: min(420px, 100%);
    position: relative;
  }
  .back-arrow-btn {
    border: 1px solid #cbd5e1;
    background: #fff;
    color: #334155;
    border-radius: 999px;
    width: 34px;
    height: 34px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 0.55rem;
    font-size: 18px;
    line-height: 1;
    font-family: var(--font-mono);
    cursor: pointer;
    transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
  }
  .back-arrow-btn:hover {
    border-color: #94a3b8;
    color: #0f172a;
    background: #f8fafc;
  }
  .search-ico {
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: #64748b;
    font-size: 13px;
    pointer-events: none;
  }
  .search-input {
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    font-size: 13px;
    color: #0f172a;
    background: #fff;
    padding: 8px 10px 8px 28px;
    outline: none;
  }
  .search-input:focus {
    border-color: #94a3b8;
    box-shadow: 0 0 0 2px rgba(148, 163, 184, 0.2);
  }

  .layout-row {
    display: grid;
    grid-template-columns: 45% minmax(0, 55%);
    gap: 12px;
    align-items: start;
  }

  .left-pane,
  .right-pane {
    min-width: 0;
  }

  .left-pane {
    position: sticky;
    top: 1rem;
  }

  @media (max-width: 1200px) {
    .page-title {
      font-size: 1.76rem;
      margin-bottom: 0.55rem;
    }
    .header-main {
      flex-direction: column;
    }
    .search-wrap {
      min-width: 0;
      width: 100%;
    }
    .layout-row {
      grid-template-columns: 1fr;
    }

    .left-pane {
      position: static;
    }
  }
  @media (max-width: 480px) {
    .page-title {
      font-size: 1.56rem;
    }
  }
</style>
