<script lang="ts">
  // Props
  export let size = 1;        // scala (1 = 100px)
  export let duration = 2;    // secondi

  // id unico per evitare collisioni se metti più loader nella stessa pagina
  const clipId = `clipping-${Math.random().toString(36).slice(2)}`;
</script>

<div
  class="loader"
  style={`--size:${size}; --time-animation:${duration}s; --clip-id:url(#${clipId});`}
  aria-label="Loading"
  role="status"
>
  <svg width="100" height="100" viewBox="0 0 100 100" aria-hidden="true">
    <defs>
      <mask id={clipId}>
        <polygon points="0,0 100,0 100,100 0,100" fill="black" />
        <polygon points="25,25 75,25 50,75" fill="white" />
        <polygon points="50,25 75,75 25,75" fill="white" />
        <polygon points="35,35 65,35 50,65" fill="white" />
        <polygon points="35,35 65,35 50,65" fill="white" />
        <polygon points="35,35 65,35 50,65" fill="white" />
        <polygon points="35,35 65,35 50,65" fill="white" />
      </mask>
    </defs>
  </svg>

  <div class="box"></div>
</div>

<style>
  .loader {
    --color-one: #ffbf48;
    --color-two: #be4a1d;
    --color-three: #ffbf4780;
    --color-four: #bf4a1d80;
    --color-five: #ffbf4740;
    --time-animation: 2s;
    --size: 1;
    --clip-id: url(#clipping);

    position: relative;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    transform: scale(var(--size));
    transform-origin: center;
    box-shadow:
      0 0 25px 0 var(--color-three),
      0 20px 50px 0 var(--color-four);
    animation: colorize calc(var(--time-animation) * 3) ease-in-out infinite;
  }

  .loader::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border-top: solid 1px var(--color-one);
    border-bottom: solid 1px var(--color-two);
    background: linear-gradient(180deg, var(--color-five), var(--color-four));
    box-shadow:
      inset 0 10px 10px 0 var(--color-three),
      inset 0 -10px 10px 0 var(--color-four);
  }

  .loader .box {
    width: 100px;
    height: 100px;
    background: linear-gradient(180deg, var(--color-one) 30%, var(--color-two) 70%);
    mask: var(--clip-id);
    -webkit-mask: var(--clip-id);
  }

  .loader svg {
    position: absolute;
    inset: 0;
  }

  /* Applichiamo animazioni ai poligoni dentro la mask */
  .loader svg mask {
    filter: contrast(15);
    animation: roundness calc(var(--time-animation) / 2) linear infinite;
  }

  .loader svg mask polygon {
    filter: blur(7px);
  }

  .loader svg mask polygon:nth-child(1) {
    transform-origin: 75% 25%;
    transform: rotate(90deg);
  }

  .loader svg mask polygon:nth-child(2) {
    transform-origin: 50% 50%;
    animation: rotation var(--time-animation) linear infinite reverse;
  }

  .loader svg mask polygon:nth-child(3) {
    transform-origin: 50% 60%;
    animation: rotation var(--time-animation) linear infinite;
    animation-delay: calc(var(--time-animation) / -3);
  }

  .loader svg mask polygon:nth-child(4) {
    transform-origin: 40% 40%;
    animation: rotation var(--time-animation) linear infinite reverse;
  }

  .loader svg mask polygon:nth-child(5) {
    transform-origin: 40% 40%;
    animation: rotation var(--time-animation) linear infinite reverse;
    animation-delay: calc(var(--time-animation) / -2);
  }

  .loader svg mask polygon:nth-child(6) {
    transform-origin: 60% 40%;
    animation: rotation var(--time-animation) linear infinite;
  }

  .loader svg mask polygon:nth-child(7) {
    transform-origin: 60% 40%;
    animation: rotation var(--time-animation) linear infinite;
    animation-delay: calc(var(--time-animation) / -1.5);
  }

  @keyframes rotation {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  @keyframes roundness {
    0% { filter: contrast(15); }
    20% { filter: contrast(3); }
    40% { filter: contrast(3); }
    60% { filter: contrast(15); }
    100% { filter: contrast(15); }
  }

  @keyframes colorize {
    0% { filter: hue-rotate(0deg); }
    20% { filter: hue-rotate(-30deg); }
    40% { filter: hue-rotate(-60deg); }
    60% { filter: hue-rotate(-90deg); }
    80% { filter: hue-rotate(-45deg); }
    100% { filter: hue-rotate(0deg); }
  }

  /* Accessibilità: rispetta "reduce motion" */
  @media (prefers-reduced-motion: reduce) {
    .loader,
    .loader::before,
    .loader svg mask,
    .loader svg mask polygon {
      animation: none !important;
      transition: none !important;
    }
  }
</style>
