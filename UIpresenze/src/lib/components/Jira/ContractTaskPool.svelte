<script lang="ts">
  import type { ContrattoCliente } from '$lib/services/clienti';

  export let contract: ContrattoCliente;
  export let taskInput = '';
  export let onTaskInput: (value: string) => void;
  export let onAppendTask: () => void;
  export let onDeleteTask: (task: string) => void;

  function handleInput(event: Event) {
    onTaskInput((event.currentTarget as HTMLInputElement).value);
  }
</script>

<div class="pool">
  <span>Pool task</span>

  <div class="task-list">
    {#each contract.pool_task as task (`${contract.id}-${task}`)}
      <span class="task-chip">
        {task}
        <button type="button" aria-label={`Rimuovi ${task}`} on:click={() => onDeleteTask(task)}>×</button>
      </span>
    {/each}
  </div>

  <div class="add-task">
    <input placeholder="PROJ-123" value={taskInput} on:input={handleInput} />
    <button type="button" on:click={onAppendTask}>Aggiungi</button>
  </div>
</div>

<style>
  .pool {
    display: grid;
    gap: 0.35rem;
    margin-top: 0.45rem;
    color: #475569;
    font-size: 0.74rem;
  }

  .task-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }

  .task-chip {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    gap: 0.25rem;
    padding: 0.2rem 0.38rem;
    border-radius: 999px;
    background: #dbeafe;
    color: #1e3a8a;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    overflow-wrap: anywhere;
  }

  .task-chip button,
  .add-task button {
    border: 0;
    border-radius: 7px;
    color: #fff;
    background: #2563eb;
    cursor: pointer;
    font: inherit;
    font-size: 0.78rem;
  }

  .task-chip button {
    flex: 0 0 auto;
    padding: 0;
    color: #1e3a8a;
    background: transparent;
    font-size: 1rem;
    line-height: 0.7;
  }

  .add-task {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.55rem;
  }

  .add-task input {
    flex: 1 1 9rem;
    min-width: 0;
    width: 100%;
    box-sizing: border-box;
    padding: 0.43rem 0.5rem;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background: #fff;
    color: #0f172a;
    font: inherit;
  }

  .add-task button {
    max-width: 100%;
    padding: 0.42rem 0.65rem;
  }
</style>
