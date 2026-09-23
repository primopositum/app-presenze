<script lang="ts">
  /** Cubo di prova con tre facce, usato solo dai test. */
  import CubeSwitcher from '../CubeSwitcher.svelte';
  import CubeFace from '../CubeFace.svelte';

  type Props = { loop?: boolean; expandable?: boolean; tall?: boolean };

  let { loop = true, expandable = false, tall = false }: Props = $props();
</script>

{#if tall}<div style="height: 1400px"></div>{/if}

<CubeSwitcher {loop} {expandable} label="Grafici" height="300px">
  <CubeFace label="Prima">
    <p data-testid="face-a">Contenuto A</p>
  </CubeFace>
  <CubeFace label="Seconda">
    <p data-testid="face-b">Contenuto B</p>
  </CubeFace>
  <CubeFace label="Terza">
    <p data-testid="face-c">Contenuto C</p>
  </CubeFace>
</CubeSwitcher>

{#if tall}<div style="height: 1400px"></div>{/if}
