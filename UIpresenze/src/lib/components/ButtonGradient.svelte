<script>
  import palette from '../../theme/palette.js';
  // Props per personalizzare il componente
  export let title = "";       // Titolo del link (per il tooltip)
  export let buttonText = "";  // Testo del bottone (passato come parametro)
  export let onClick;         // Funzione da chiamare al click
  export let disabled = false;
</script>

<!-- Struttura HTML con classi Tailwind -->
<div class="flex justify-center items-center">
  <div class="relative inline-flex group">
    <div
      class="absolute transition-all duration-1000 opacity-70 -inset-px rounded-xl blur-lg group-hover:opacity-100 group-hover:-inset-1 group-hover:duration-200 animate-tilt"
      style={`background-image: linear-gradient(90deg, ${palette.gradient.from}, ${palette.gradient.via}, ${palette.gradient.to});`}
    ></div>
    <button
      on:click={onClick}
      title={title}
      disabled={disabled}
      class="relative inline-flex items-center justify-center px-4 py-2.5 text-sm font-bold text-white transition-all duration-200 bg-gray-700 font-pj rounded-xl focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900 disabled:opacity-60 disabled:cursor-not-allowed sm:px-6 sm:py-3 sm:text-base lg:px-8 lg:py-4 lg:text-lg"
    >
      {buttonText}
    </button>
  </div>
</div>

<!-- Stili aggiuntivi per l'animazione -->
<style>
  @keyframes tilt {
    0%, 100% { transform: rotate(0deg); }
    50% { transform: rotate(2deg); }
  }
  .animate-tilt {
    animation: tilt 3s ease-in-out infinite;
  }
</style>
