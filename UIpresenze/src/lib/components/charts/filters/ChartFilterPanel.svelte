<script lang="ts">
  /**
   * Pannello dei filtri della schermata attiva del cubo.
   *
   * Si applica mentre si scrive: i grafici sono derivati dallo store e si
   * ridisegnano da soli, un pulsante "applica" aggiungerebbe solo un passaggio.
   * I filtri tecnici restano nascosti finche' non servono, ma si vedono sempre
   * se ce n'e' uno acceso: un filtro attivo e invisibile e' il peggiore.
   */
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faXmark } from '@fortawesome/free-solid-svg-icons';
  import { chartsData } from '$lib/remo/chartsData';
  import FilterField from './FilterField.svelte';
  import {
    activeCount,
    chartFilters,
    isDefault,
    resetFilter,
    resetFilters,
    resolveValues,
    setFilterValue
  } from './core/filterState';
  import { filterOptions } from './options';
  import type { FilterDef, FilterGroup, FilterScreen } from './core/types';

  type Props = {
    screen: FilterScreen;
    onclose?: () => void;
  };

  let { screen, onclose }: Props = $props();

  let showTechnical = $state(false);

  const stored = $derived($chartFilters[screen.id]);
  const values = $derived(resolveValues(screen, stored));
  const active = $derived(activeCount(screen, stored));
  const technicalCount = $derived(
    screen.groups.flatMap((group) => group.filters).filter((def) => def.technical).length
  );

  /** Le frecce servono ai campi, non al cubo; Esc chiude il pannello e non riduce il cubo. */
  function handleKeydown(event: KeyboardEvent) {
    event.stopPropagation();
    if (event.key === 'Escape') {
      event.preventDefault();
      onclose?.();
    }
  }

  function visible(def: FilterDef) {
    return !def.technical || showTechnical || !isDefault(def, values[def.id]);
  }

  function groupActive(group: FilterGroup) {
    return group.filters.filter((def) => !isDefault(def, values[def.id])).length;
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<aside
  class="filter-panel"
  aria-label={`Filtri: ${screen.title}`}
  data-history-hover-exclude
  data-cube-no-drag
  onkeydown={handleKeydown}
>
  <header>
    <div>
      <h3>Filtri</h3>
      <p>{screen.title}{#if screen.description} · {screen.description}{/if}</p>
    </div>
    <button type="button" class="close" aria-label="Chiudi i filtri" title="Chiudi (Esc)" onclick={() => onclose?.()}>
      <FontAwesomeIcon icon={faXmark} />
    </button>
  </header>

  <div class="toolbar">
    <span class="summary" class:on={active > 0}>
      {active === 0 ? 'Nessun filtro attivo' : `${active} ${active === 1 ? 'filtro attivo' : 'filtri attivi'}`}
    </span>
    <div class="toolbar-actions">
      {#if technicalCount > 0}
        <button
          type="button"
          class="pill"
          aria-pressed={showTechnical}
          onclick={() => (showTechnical = !showTechnical)}
        >
          {showTechnical ? 'Nascondi' : 'Mostra'} tecnici ({technicalCount})
        </button>
      {/if}
      <button type="button" class="pill" disabled={active === 0} onclick={() => resetFilters(screen.id)}>
        Ripristina tutto
      </button>
    </div>
  </div>

  <div class="groups">
    {#each screen.groups as group (group.id)}
      {@const fields = group.filters.filter(visible)}
      {#if fields.length > 0}
        <details open>
          <summary>
            <span>{group.label}</span>
            {#if groupActive(group) > 0}<span class="badge">{groupActive(group)}</span>{/if}
          </summary>
          {#if group.description}<p class="group-note">{group.description}</p>{/if}
          <div class="fields">
            {#each fields as def (def.id)}
              <FilterField
                {def}
                value={values[def.id]}
                options={filterOptions(def, $chartsData)}
                modified={!isDefault(def, values[def.id])}
                onchange={(next) => setFilterValue(screen.id, def.id, next)}
                onreset={() => resetFilter(screen, def.id)}
              />
            {/each}
          </div>
        </details>
      {/if}
    {/each}
  </div>
</aside>

<style>
  .filter-panel {
    position: absolute;
    z-index: 4;
    top: 54px;
    right: 8px;
    bottom: 8px;
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr);
    width: min(380px, calc(100% - 16px));
    box-sizing: border-box;
    border: 1px solid #0f172a;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 24px 60px rgba(2, 6, 23, 0.45);
    overflow: hidden;
    animation: panel-in 160ms ease-out;
  }

  @keyframes panel-in {
    from {
      opacity: 0;
      transform: translateY(-6px);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .filter-panel {
      animation: none;
    }
  }

  header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.75rem 0.85rem 0.65rem;
    background: #0f172a;
  }

  h3 {
    margin: 0;
    color: #fff;
    font-size: 0.86rem;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  header p {
    margin: 0.2rem 0 0;
    color: #94a3b8;
    font-size: 0.66rem;
    font-family: var(--font-mono);
    line-height: 1.35;
  }

  .close {
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    width: 28px;
    height: 28px;
    border: 1px solid #334155;
    border-radius: 999px;
    background: #1e293b;
    color: #cbd5e1;
    font-size: 0.78rem;
    cursor: pointer;
  }

  .close:hover {
    color: #fff;
    border-color: #64748b;
  }

  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.4rem;
    border-bottom: 1px solid #e2e8f0;
    padding: 0.5rem 0.85rem;
    background: #f8fafc;
  }

  .summary {
    color: #64748b;
    font-size: 0.66rem;
    font-family: var(--font-mono);
  }

  .summary.on {
    color: #0f172a;
  }

  .summary.on::before {
    content: '';
    display: inline-block;
    width: 7px;
    height: 7px;
    margin-right: 0.35rem;
    border-radius: 999px;
    background: #f97316;
    vertical-align: 1px;
  }

  .toolbar-actions {
    display: flex;
    gap: 0.3rem;
  }

  .pill {
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    padding: 0.2rem 0.55rem;
    background: #fff;
    color: #475569;
    font-size: 0.64rem;
    font-family: var(--font-mono);
    cursor: pointer;
  }

  .pill:hover:not(:disabled) {
    border-color: #94a3b8;
    color: #0f172a;
  }

  .pill[aria-pressed='true'] {
    border-color: #0f172a;
    color: #0f172a;
  }

  .pill:disabled {
    opacity: 0.45;
    cursor: default;
  }

  .groups {
    overflow: auto;
    padding: 0.2rem 0.85rem 0.85rem;
    overscroll-behavior: contain;
  }

  details {
    border-bottom: 1px solid #eef2f6;
    padding: 0.55rem 0;
  }

  details:last-child {
    border-bottom: 0;
  }

  summary {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: #475569;
    font-size: 0.66rem;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    cursor: pointer;
    list-style: none;
  }

  summary::-webkit-details-marker {
    display: none;
  }

  summary::before {
    content: '▸';
    color: #94a3b8;
    font-size: 0.6rem;
    transition: transform 0.15s ease;
  }

  details[open] > summary::before {
    transform: rotate(90deg);
  }

  .badge {
    border-radius: 999px;
    padding: 0.02rem 0.38rem;
    background: #f97316;
    color: #fff;
    font-size: 0.58rem;
  }

  .group-note {
    margin: 0.35rem 0 0;
    color: #94a3b8;
    font-size: 0.62rem;
    font-family: var(--font-mono);
  }

  .fields {
    display: grid;
    gap: 0.8rem;
    padding: 0.6rem 0 0.2rem;
  }
</style>
