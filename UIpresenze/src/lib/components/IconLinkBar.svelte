<script>
  import { faConfluence, faJira } from '@fortawesome/free-brands-svg-icons';
  import { faCircle } from '@fortawesome/free-regular-svg-icons';
  import { faCar } from '@fortawesome/free-solid-svg-icons';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import palette from '../../theme/palette.js';
	import { goto } from '$app/navigation';
  
</script>

<div
  class="mt-8 flex justify-center "
  style={`--icon-hover-color: ${palette.state.info};
    --icon-violet-color: ${palette.accent.violet};
    --icon-auto-color: #16a34a;`}
>
  <div class="rounded-[4%] border-[10px] border-gray-800 bg-white p-8 shadow-lg overflow-hidden">  
    <a href="https://primopositum.atlassian.net/wiki/spaces" target="_blank" class="icon-container">
      <FontAwesomeIcon icon={faConfluence} class="text-gray-700 text-[280%]" />
    </a>
    <a href="https://primopositum.atlassian.net/issues/?filter=10013" target="_blank" class="icon-container">
      <FontAwesomeIcon icon={faJira} class="text-gray-700 text-[280%]" />
    </a>
    <a href="https://primopositum.odoo.com/odoo" target="_blank" class="icon-container violet-icon">
      <FontAwesomeIcon icon={faCircle} class="text-gray-700 font-black text-[280%]" />
    </a>
      <button type="button" class="icon-container auto-icon" on:click={() => goto('/auto')} aria-label="Vai alla pagina auto">
        <FontAwesomeIcon icon={faCar} class="text-gray-700 text-[280%]" />
      </button>
    </div>
  </div>

<style>
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
    color: var(--icon-hover-color);
  }

  .icon-container:hover::after {
    clip-path: circle(70% at center);
  }
  
  .violet-icon:hover :global(svg) {
    color: var(--icon-violet-color);
  }

  .auto-icon:hover :global(svg) {
    color: var(--icon-auto-color);
  }
</style>
