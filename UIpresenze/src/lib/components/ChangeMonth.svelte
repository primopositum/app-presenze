<script lang="ts">
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faBackward, faForward} from '@fortawesome/free-solid-svg-icons';
  import palette from '../../theme/palette.js';
  export let year: number;
  export let month: number; // 1-12
  export let loading: boolean = false;
  export let onprev: () => void;
  export let onnext: () => void;
  
  const monthNames = [
    'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
    'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
  ];
</script>

<div
  class="flex flex-wrap items-center justify-center gap-2"
  style={`--btn-hover-bg: ${palette.background.muted};`}
>
  <button on:click={onprev} disabled={loading}>
    <FontAwesomeIcon
      icon={faBackward}
      class="text-[150%]"
      style={`color: ${palette.secondary.main};`}
    />
  </button>
  <span style={`color: ${palette.primary.main};`}>
    {monthNames[month - 1]} {year}
  </span>
  <button on:click={onnext} disabled={loading}>
    <FontAwesomeIcon
      icon={faForward}
      class="text-[150%]"
      style={`color: ${palette.secondary.main};`}
    />
  </button>
</div>

<style>  
  button {
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    transition: background 0.2s;
  }
  
  button:hover:not(:disabled) {
    background: var(--btn-hover-bg);
  }
  
  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  span {
    font-size: clamp(0.9rem, 2.4vw, 1.1rem);
    font-weight: 600;
    min-width: 0;
    text-align: center;
    white-space: nowrap;
  }

  @media (max-width: 520px) {
    button {
      padding: 6px 10px;
    }
  }
</style>
