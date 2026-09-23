<script lang="ts">
  /**
   * Un filtro del pannello: il controllo lo decide il `type` della definizione.
   * Non conosce lo store: riceve il valore e restituisce il nuovo con `onchange`.
   */
  import { regexError } from './core/primitives';
  import type {
    DateSpan,
    FilterDef,
    FilterOption,
    FilterValue,
    NumberRange
  } from './core/types';

  type Props = {
    def: FilterDef;
    value: FilterValue;
    options?: FilterOption[];
    modified?: boolean;
    onchange: (value: FilterValue) => void;
    onreset?: () => void;
  };

  let { def, value, options = [], modified = false, onchange, onreset }: Props = $props();

  /** Oltre questa soglia le opzioni diventano un elenco con ricerca. */
  const CHIP_LIMIT = 8;
  /**
   * Voci disegnate per volta: con migliaia di issue l'elenco completo costerebbe
   * piu' dei grafici. Si affina con la ricerca.
   */
  const RENDER_LIMIT = 100;

  let query = $state('');

  const fieldId = $derived(`chart-filter-${def.id}`);
  const selected = $derived(Array.isArray(value) ? value : []);
  const range = $derived((value ?? { min: null, max: null }) as NumberRange);
  const span = $derived((value ?? { from: '', to: '' }) as DateSpan);
  const asList = $derived(options.length > CHIP_LIMIT);
  const visibleOptions = $derived.by(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return options;
    return options.filter(
      (option) =>
        option.label.toLowerCase().includes(needle) || option.value.toLowerCase().includes(needle)
    );
  });
  const shownOptions = $derived(visibleOptions.slice(0, RENDER_LIMIT));
  const hiddenCount = $derived(visibleOptions.length - shownOptions.length);
  const chosen = $derived(
    def.type === 'select' && value ? options.find((option) => option.value === value) : undefined
  );
  const patternError = $derived(def.type === 'regex' ? regexError(String(value ?? '')) : '');
  const unit = $derived('unit' in def ? def.unit : undefined);
  const step = $derived('step' in def ? def.step : undefined);
  const min = $derived('min' in def ? def.min : undefined);
  const max = $derived('max' in def ? def.max : undefined);
  const placeholder = $derived('placeholder' in def ? def.placeholder : undefined);

  function toNumber(text: string): number | null {
    if (text.trim() === '') return null;
    const parsed = Number(text.replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : null;
  }

  function toggleOption(optionValue: string) {
    onchange(
      selected.includes(optionValue)
        ? selected.filter((item) => item !== optionValue)
        : [...selected, optionValue]
    );
  }
</script>

<div class="field" class:modified class:technical={def.technical}>
  <div class="field-head">
    <label for={fieldId}>
      {def.label}
      {#if def.technical}<span class="tag">tecnico</span>{/if}
    </label>
    {#if modified && onreset}
      <button type="button" class="link" onclick={onreset}>ripristina</button>
    {/if}
  </div>

  {#if def.type === 'multiselect'}
    {#if options.length === 0}
      <p class="empty">Nessuna voce nei dati caricati.</p>
    {:else if !asList}
      <div class="chips" role="group" aria-label={def.label} id={fieldId}>
        {#each options as option (option.value)}
          <button
            type="button"
            class="chip"
            class:on={selected.includes(option.value)}
            aria-pressed={selected.includes(option.value)}
            title={option.hint}
            onclick={() => toggleOption(option.value)}
          >
            {option.label}
          </button>
        {/each}
      </div>
    {:else}
      <div class="list-tools">
        <input
          id={fieldId}
          type="search"
          class="input"
          placeholder={`Cerca fra ${options.length} voci`}
          bind:value={query}
        />
        <button
          type="button"
          class="link"
          onclick={() =>
            onchange([...new Set([...selected, ...visibleOptions.map((option) => option.value)])])}
        >
          tutti
        </button>
        <button type="button" class="link" disabled={selected.length === 0} onclick={() => onchange([])}>
          nessuno
        </button>
      </div>
      <ul class="option-list" aria-label={def.label}>
        {#each shownOptions as option (option.value)}
          <li>
            <label class="option">
              <input
                type="checkbox"
                checked={selected.includes(option.value)}
                onchange={() => toggleOption(option.value)}
              />
              <span class="option-label">{option.label}</span>
              {#if option.hint}<span class="option-hint">{option.hint}</span>{/if}
            </label>
          </li>
        {:else}
          <li class="empty">Nessuna voce corrisponde.</li>
        {/each}
      </ul>
      <p class="count">
        {selected.length === 0 ? 'Tutte le voci incluse' : `${selected.length} di ${options.length} selezionate`}
        {#if hiddenCount > 0} · altre {hiddenCount}: affina la ricerca{/if}
      </p>
    {/if}
  {:else if def.type === 'select'}
    {#if chosen || value}
      <div class="chosen">
        <span class="chosen-label">{chosen?.label ?? value}</span>
        {#if chosen?.hint}<span class="option-hint">{chosen.hint}</span>{/if}
        <button type="button" class="link" onclick={() => onchange('')}>rimuovi</button>
      </div>
    {/if}
    {#if options.length === 0}
      <p class="empty">Nessuna voce nei dati caricati.</p>
    {:else}
      <input
        id={fieldId}
        type="search"
        class="input"
        placeholder={def.placeholder ?? `Cerca fra ${options.length} voci`}
        bind:value={query}
      />
      <ul class="option-list" role="listbox" aria-label={def.label}>
        {#each shownOptions as option (option.value)}
          <li>
            <label class="option">
              <input
                type="radio"
                name={fieldId}
                checked={value === option.value}
                onchange={() => onchange(option.value)}
              />
              <span class="option-label">{option.label}</span>
              {#if option.hint}<span class="option-hint">{option.hint}</span>{/if}
            </label>
          </li>
        {:else}
          <li class="empty">Nessuna voce corrisponde.</li>
        {/each}
      </ul>
      {#if hiddenCount > 0}
        <p class="count">Mostrate {shownOptions.length} di {visibleOptions.length}: affina la ricerca.</p>
      {/if}
    {/if}
  {:else if def.type === 'segmented'}
    <div class="segmented" role="radiogroup" aria-label={def.label} id={fieldId}>
      {#each def.options as option (option.value)}
        <button
          type="button"
          role="radio"
          class:on={value === option.value}
          aria-checked={value === option.value}
          onclick={() => onchange(option.value)}
        >
          {option.label}
        </button>
      {/each}
    </div>
  {:else if def.type === 'range'}
    <div class="pair">
      <div class="affix">
        <input
          id={fieldId}
          class="input"
          type="number"
          inputmode="decimal"
          aria-label={`${def.label} minimo`}
          placeholder="min"
          {step}
          {min}
          {max}
          value={range.min ?? ''}
          oninput={(event) => onchange({ ...range, min: toNumber(event.currentTarget.value) })}
        />
        {#if unit}<span>{unit}</span>{/if}
      </div>
      <span class="dash">–</span>
      <div class="affix">
        <input
          class="input"
          type="number"
          inputmode="decimal"
          aria-label={`${def.label} massimo`}
          placeholder="max"
          {step}
          {min}
          {max}
          value={range.max ?? ''}
          oninput={(event) => onchange({ ...range, max: toNumber(event.currentTarget.value) })}
        />
        {#if unit}<span>{unit}</span>{/if}
      </div>
    </div>
    {#if range.min !== null && range.max !== null && range.min > range.max}
      <p class="error">Il minimo supera il massimo: nessun dato passera' il filtro.</p>
    {/if}
  {:else if def.type === 'number'}
    <div class="affix single">
      <input
        id={fieldId}
        class="input"
        type="number"
        inputmode="decimal"
        {step}
        {min}
        {max}
        {placeholder}
        value={typeof value === 'number' ? value : ''}
        oninput={(event) => onchange(toNumber(event.currentTarget.value))}
      />
      {#if unit}<span>{unit}</span>{/if}
    </div>
  {:else if def.type === 'text' || def.type === 'regex'}
    <div class="affix single" class:regex={def.type === 'regex'}>
      {#if def.type === 'regex'}<span class="slash">/</span>{/if}
      <input
        id={fieldId}
        class="input"
        class:invalid={patternError}
        type="text"
        spellcheck="false"
        autocomplete="off"
        {placeholder}
        value={String(value ?? '')}
        oninput={(event) => onchange(event.currentTarget.value)}
      />
      {#if def.type === 'regex'}<span class="slash">/i</span>{/if}
    </div>
    {#if patternError}<p class="error">{patternError}. Il filtro viene ignorato.</p>{/if}
  {:else if def.type === 'date'}
    <input
      id={fieldId}
      class="input"
      type="date"
      value={String(value ?? '')}
      oninput={(event) => onchange(event.currentTarget.value)}
    />
  {:else if def.type === 'dateRange'}
    <div class="pair">
      <input
        id={fieldId}
        class="input"
        type="date"
        aria-label={`${def.label}: dal`}
        max={span.to || undefined}
        value={span.from}
        oninput={(event) => onchange({ ...span, from: event.currentTarget.value })}
      />
      <span class="dash">–</span>
      <input
        class="input"
        type="date"
        aria-label={`${def.label}: al`}
        min={span.from || undefined}
        value={span.to}
        oninput={(event) => onchange({ ...span, to: event.currentTarget.value })}
      />
    </div>
  {:else if def.type === 'toggle'}
    <button
      id={fieldId}
      type="button"
      role="switch"
      class="switch"
      aria-checked={value === true}
      onclick={() => onchange(value !== true)}
    >
      <span class="knob"></span>
      <span class="switch-label">{value === true ? 'Attivo' : 'Spento'}</span>
    </button>
  {/if}

  {#if def.help}<p class="help">{def.help}</p>{/if}
</div>

<style>
  .field {
    display: grid;
    gap: 0.35rem;
    min-width: 0;
    border-left: 2px solid transparent;
    padding-left: 0.5rem;
    margin-left: -0.5rem;
    transition: border-color 0.15s ease;
  }

  /* Il filo arancio e' lo stesso del tab attivo: dice "qui c'e' qualcosa di acceso". */
  .field.modified {
    border-left-color: #f97316;
  }

  .field-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .field-head label {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    color: #0f172a;
    font-size: 0.68rem;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .tag {
    border-radius: 999px;
    padding: 0.05rem 0.35rem;
    background: #f1f5f9;
    color: #64748b;
    font-size: 0.56rem;
    letter-spacing: 0.02em;
  }

  .link {
    border: 0;
    padding: 0;
    background: none;
    color: #64748b;
    font-size: 0.64rem;
    font-family: var(--font-mono);
    text-decoration: underline;
    text-underline-offset: 2px;
    cursor: pointer;
  }

  .link:hover:not(:disabled) {
    color: #0f172a;
  }

  .link:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .input {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 0.35rem 0.5rem;
    background: #fff;
    color: #0f172a;
    font-size: 0.74rem;
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    box-shadow: none;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }

  .input:focus {
    outline: none;
    border-color: #0f172a;
    box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.08);
  }

  .input.invalid {
    border-color: #d03b3b;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }

  .chip,
  .segmented button {
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    padding: 0.22rem 0.6rem;
    background: #fff;
    color: #475569;
    font-size: 0.68rem;
    font-family: var(--font-mono);
    cursor: pointer;
    transition: border-color 0.15s ease, color 0.15s ease, background-color 0.15s ease;
  }

  .chip:hover,
  .segmented button:hover {
    border-color: #94a3b8;
    color: #0f172a;
  }

  .chip.on,
  .segmented button.on {
    border-color: #0f172a;
    background: #0f172a;
    color: #fff;
  }

  .segmented {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }

  .list-tools {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .option-list {
    display: grid;
    max-height: 176px;
    overflow: auto;
    margin: 0;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.2rem;
    list-style: none;
    overscroll-behavior: contain;
  }

  .option {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.45rem;
    border-radius: 6px;
    padding: 0.28rem 0.4rem;
    cursor: pointer;
  }

  .option:hover {
    background: #f8fafc;
  }

  .option input {
    width: 13px;
    height: 13px;
    margin: 0;
    border-radius: 3px;
    border-color: #94a3b8;
    color: #0f172a;
  }

  .chosen {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    align-items: center;
    gap: 0.5rem;
    border: 1px solid #0f172a;
    border-radius: 8px;
    padding: 0.35rem 0.5rem;
    background: #f8fafc;
  }

  .chosen-label {
    overflow: hidden;
    color: #0f172a;
    font-size: 0.72rem;
    font-family: var(--font-mono);
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .option input[type='radio'] {
    border-radius: 999px;
  }

  .option-label {
    overflow: hidden;
    color: #0f172a;
    font-size: 0.7rem;
    font-family: var(--font-mono);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .option-hint,
  .count {
    color: #94a3b8;
    font-size: 0.62rem;
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .count {
    margin: 0;
  }

  .pair {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    align-items: center;
    gap: 0.35rem;
  }

  .dash {
    color: #94a3b8;
    font-size: 0.72rem;
  }

  .affix {
    position: relative;
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .affix > span {
    flex: 0 0 auto;
    margin-left: 0.3rem;
    color: #64748b;
    font-size: 0.66rem;
    font-family: var(--font-mono);
  }

  .affix.single {
    max-width: 220px;
  }

  .affix.regex {
    max-width: none;
  }

  .affix .slash {
    margin: 0 0.25rem;
    color: #94a3b8;
    font-size: 0.8rem;
  }

  .affix .slash:first-child {
    margin-left: 0;
  }

  .switch {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    width: fit-content;
    border: 0;
    padding: 0;
    background: none;
    cursor: pointer;
  }

  .knob {
    position: relative;
    width: 30px;
    height: 17px;
    border-radius: 999px;
    background: #cbd5e1;
    transition: background-color 0.15s ease;
  }

  .knob::after {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 13px;
    height: 13px;
    border-radius: 999px;
    background: #fff;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.25);
    transition: transform 0.15s ease;
  }

  .switch[aria-checked='true'] .knob {
    background: #0f172a;
  }

  .switch[aria-checked='true'] .knob::after {
    transform: translateX(13px);
  }

  .switch-label {
    color: #475569;
    font-size: 0.68rem;
    font-family: var(--font-mono);
  }

  .help,
  .empty,
  .error {
    margin: 0;
    color: #94a3b8;
    font-size: 0.62rem;
    font-family: var(--font-mono);
    line-height: 1.35;
  }

  .empty {
    padding: 0.3rem 0.4rem;
  }

  .error {
    color: #b91c1c;
  }
</style>
