<script lang="ts">
  import { goto } from '$app/navigation';

  export let status: number;
  export let error: Error;

  const isNotFound = status === 404;
  const title = isNotFound ? 'Pagina non trovata' : 'Errore';
  const message = isNotFound
    ? 'La pagina che cerchi non esiste.'
    : error?.message ?? 'Si è verificato un errore inatteso.';
</script>

<div class="flex flex-col items-center justify-center gap-4 py-16">
  <h1 class="text-3xl font-bold">{title}</h1>
  <p class="text-gray-600 text-center max-w-lg">{message}</p>
  <div class="flex items-center gap-3">
    <button
      class="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition"
      on:click={() => goto('/')}
    >
     Torna alla home
    </button>
  </div>
</div>
