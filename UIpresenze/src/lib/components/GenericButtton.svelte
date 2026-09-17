<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let color = '#374151';
  export let disabled = false;
  export let label = 'Azione';
  export let title = label;
  export let type: 'button' | 'submit' | 'reset' = 'button';

  const dispatch = createEventDispatcher<{ click: MouseEvent }>();

  function handleClick(event: MouseEvent) {
    if (disabled) return;
    dispatch('click', event);
  }
</script>

<button
  class="genericButtton"
  style={`--generic-button-color: ${color};`}
  {type}
  {disabled}
  aria-label={label}
  {title}
  on:click={handleClick}
>
  <slot />
</button>

<style>
  .genericButtton {
    appearance: none;
    width: 42px;
    height: 42px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    border: 1px solid color-mix(in srgb, var(--generic-button-color) 48%, #ffffff);
    border-radius: 10px;
    background: #ffffff;
    color: var(--generic-button-color);
    font-size: 1.05rem;
    font-weight: 800;
    line-height: 1;
    cursor: pointer;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
    transition:
      background 140ms ease,
      border-color 140ms ease,
      color 140ms ease,
      transform 120ms ease,
      box-shadow 140ms ease;
  }

  .genericButtton:hover:not(:disabled) {
    background: color-mix(in srgb, var(--generic-button-color) 8%, #ffffff);
    border-color: var(--generic-button-color);
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.14);
    transform: translateY(-1px);
  }

  .genericButtton:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
  }

  .genericButtton:focus-visible {
    outline: 2px solid color-mix(in srgb, var(--generic-button-color) 34%, transparent);
    outline-offset: 2px;
  }

  .genericButtton:disabled {
    cursor: not-allowed;
    opacity: 0.55;
    box-shadow: none;
  }

  .genericButtton :global(svg) {
    display: block;
  }
</style>
