<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import type { IconDefinition } from '@fortawesome/fontawesome-svg-core';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import {
    faConfluence,
    faJira,
    faAmazon,
    faAws,
    faDiscord,
    faGithub,
    faGitlab,
    faLinkedin,
    faMicrosoft,
    faNotion,
    faUbuntu
  } from '@fortawesome/free-brands-svg-icons';
  import { faCircle } from '@fortawesome/free-regular-svg-icons';
  import { faCar } from '@fortawesome/free-solid-svg-icons';
  import palette from '../../theme/palette.js';
  import { getUtilitiesBar, type UtilitiesBarItem } from '$lib/services/utilitiesbar';

  const ICON_MAP: Record<string, IconDefinition> = {
    faConfluence,
    faJira,
    faCircle,
    faAmazon,
    faAws,
    faDiscord,
    faGithub,
    faGitlab,
    faLinkedin,
    faMicrosoft,
    faNotion,
    faUbuntu
  };

  const DEFAULT_HOVER = palette.state.info;
  let items: UtilitiesBarItem[] = [];

  function normalizeColor(value: string) {
    const color = String(value || '').trim();
    if (/^#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/.test(color)) return color;
    return DEFAULT_HOVER;
  }

  onMount(async () => {
    try {
      const rows = await getUtilitiesBar();
      items = (Array.isArray(rows) ? rows : [])
        .filter((item) => item?.link && item?.icon && ICON_MAP[item.icon])
        .sort((a, b) => Number(a.posizione || 0) - Number(b.posizione || 0));
    } catch (e) {
      items = [];
      console.error('Errore caricamento utilitiesbar', e);
    }
  });
</script>

<div class="utility-shell" style={`--icon-auto-color: #16a34a;`}>
  <div class="utility-card rounded-[4%] border-[10px] border-gray-800 bg-white p-8 shadow-lg overflow-hidden">
    <button type="button" class="icon-container auto-icon" on:click={() => goto('/auto')} aria-label="Vai alla pagina auto">
      <FontAwesomeIcon icon={faCar} class="text-gray-700 text-[280%]" />
    </button>

    {#each items as item (item.id)}
      <a
        href={item.link}
        target="_blank"
        rel="noopener noreferrer"
        class="icon-container"
        style={`--item-hover-color: ${normalizeColor(item.colore)};`}
      >
        <FontAwesomeIcon icon={ICON_MAP[item.icon]} class="text-gray-700 text-[280%]" />
      </a>
    {/each}
  </div>
</div>

<style>
  .utility-shell {
    margin-top: 2rem;
    display: flex;
    justify-content: center;
    padding-inline: 1rem;
    /* Evita sovrapposizione con HourBalance fixed in basso a destra */
    padding-bottom: 190px;
  }

  .utility-card {
    max-width: min(100%, 760px);
  }

  .icon-container {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    padding: 0;
    cursor: pointer;
  }

  .icon-container :global(svg) {
    position: relative;
    z-index: 1;
    transition: color 0.5s ease;
  }

  .icon-container:hover :global(svg) {
    color: var(--item-hover-color, #0ea5e9);
  }

  .auto-icon:hover :global(svg) {
    color: var(--icon-auto-color);
  }

  @media (max-width: 900px) {
    .utility-shell {
      padding-bottom: 170px;
    }

    .utility-card {
      border-width: 8px;
      padding: 1rem;
    }
  }

  @media (max-width: 640px) {
    .utility-shell {
      padding-bottom: 1rem;
    }
  }
</style>
