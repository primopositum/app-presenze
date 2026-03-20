
<script lang="ts">
    import type { Trasferta } from '$lib/services/trasferte';
    import { useDeleteTrasferta } from '$lib/hooks/useTrasferte';
    import { timeEntryReload } from '$lib/stores/timeEntryReload';
    import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
    import { faTrash } from '@fortawesome/free-solid-svg-icons';

    export let trasf: Trasferta | null = null;
    export let onClick: ((trasf: Trasferta) => void) | undefined;
    let deleting = false;

    function handleClick() {
        if (!trasf) return;
        onClick?.(trasf);
    }

    async function handleDelete(event: MouseEvent) {
        event.stopPropagation();
        if (!trasf || deleting) return;
        if (trasf.validation_level === 2) return;
        try {
            deleting = true;
            const del = useDeleteTrasferta({ tId: String(trasf.id) });
            await del();
            timeEntryReload.bump();
        } catch (e) {
            console.error('Errore cancellazione trasferta', e);
        } finally {
            deleting = false;
        }
    }
    
  function validationBg(level: number | undefined) {
    if (level === 1) return 'is-sent';
    if (level === 2) return 'is-validated';
    return '';
  }
</script>
<li
    class={`card ${validationBg(trasf?.validation_level)}`}
    role="button"
    tabindex="0"
    on:click={handleClick}
    on:keydown={(e) => e.key === 'Enter' && handleClick()}
>

    <div class="head ${validationBg(trasf?.validation_level)}">
        <div class="title">{trasf?.azienda || `Trasferta #${trasf?.id ?? ''}`}</div>
        {#if trasf?.validation_level !== 2}
            <button
                type="button"
                class="trash"
                on:click={handleDelete}
                disabled={deleting}
                aria-label="Elimina trasferta"
                title="Elimina"
            >
                <FontAwesomeIcon icon={faTrash} class="text-sm text-slate-600" />
            </button>
        {/if}
    </div>
    <div class="subtitle">{trasf?.data || ''} || {trasf?.utente_nome || ''} {trasf?.utente_cognome || ''}</div>
</li>



<style>
    
    .title {
        font-weight: 600;
        color: #111827;
    }

    .subtitle {
        margin-top: 4px;
        color: #6b7280;
        font-size: 0.9rem;
    }

    .card {
        position: relative;
        overflow: hidden;
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 12px 14px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        cursor: pointer;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }

    .card.is-sent {
        background: #fee2e2;
    }

    .card.is-validated {
        background: #dcfce7;
        border-color: #86efac;
    }

    .card.is-validated::before {
        content: 'VALIDATE';
        position: absolute;
        right: -8px;
        bottom: -6px;
        font-family: 'infinity', sans-serif;
        font-size: 2.5rem;
        letter-spacing: 0.08em;
        color: rgba(22, 101, 52, 0.15);
        transform: rotate(-18deg);
        pointer-events: none;
        user-select: none;
        z-index: 0;
        white-space: nowrap;
    }

    .head,
    .subtitle {
        position: relative;
        z-index: 1;
    }

    .card:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
    }

    .head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
    }

    .head.is-validated .title {
        color: #166534;
    }

    .trash {
        width: 34px;
        height: 34px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        background: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
    }

    .trash:hover:not(:disabled) {
        background: #fef2f2;
        border-color: #fecaca;
    }

    .trash:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

</style>
