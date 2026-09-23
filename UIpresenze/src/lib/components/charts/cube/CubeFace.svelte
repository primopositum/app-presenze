<script lang="ts">
  /**
   * Una faccia del CubeSwitcher: si registra nel cubo padre e da sola calcola
   * la propria posizione nello spazio 3D. Il contenuto e' una schermata qualsiasi.
   *
   * A cubo fermo la faccia esce dallo spazio 3D (`cube.settled`) e torna un
   * normale riquadro che scorre: e' l'unico modo perche' rotella, passaggio del
   * mouse e tooltip funzionino su tutte le schermate, non solo su alcune.
   */
  import { getContext, onDestroy, type Snippet } from 'svelte';
  import { CUBE_CONTEXT_KEY, type CubeContext } from './cube';

  type Props = {
    label?: string;
    tint?: string;
    /** Id della schermata di filtri da aprire con il pulsante del cubo. */
    filters?: string;
    children?: Snippet;
  };

  let { label, tint, filters, children }: Props = $props();

  const cube = getContext<CubeContext>(CUBE_CONTEXT_KEY);
  if (!cube) throw new Error('<CubeFace> va usato dentro <CubeSwitcher>.');

  const id = Symbol('cube-face');
  cube.register(
    id,
    () => label,
    () => tint,
    () => filters
  );
  onDestroy(() => cube.unregister(id));

  const index = $derived(cube.indexOf(id));
  const active = $derived(index >= 0 && cube.isActive(index));
  const mounted = $derived(index >= 0 && cube.isMounted(index));
</script>

<div
  class="cube-face"
  class:active
  style:--face-tint={tint ?? '#ffffff'}
  style:transform={cube.settled
    ? 'none'
    : `rotateY(${cube.angle * Math.max(0, index)}deg) translateZ(${cube.depth}px)`}
  style:visibility={index >= 0 && (!cube.settled || active) ? 'visible' : 'hidden'}
  inert={!active}
  aria-hidden={!active}
>
  {#if mounted}
    {@render children?.()}
  {/if}
</div>

<style>
  .cube-face {
    position: absolute;
    inset: 0;
    /* Contenuto piu' grande della faccia: si scorre, non si comprime. */
    overflow: auto;
    box-sizing: border-box;
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    background: var(--face-tint);
    /* Le facce opposte non devono comparire a rovescio durante la rotazione. */
    backface-visibility: hidden;
    /* A schermo intero la pagina dietro non deve scorrere insieme alla faccia. */
    overscroll-behavior: contain;
  }

  .cube-face.active {
    box-shadow: 0 18px 40px rgba(15, 23, 42, 0.18);
  }
</style>
