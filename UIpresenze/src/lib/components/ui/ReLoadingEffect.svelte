<script>
  export let size = "text-2xl";  // puoi passare classi Tailwind per la dimensione
  export let color = "text-gray-500"; // oppure personalizzare il colore
  export let speed = "animate-spin-slow"; // velocità custom
</script>

<style>
  /* Rotazione personalizzata, più fluida e lenta di animate-spin */
  @keyframes spin-slow {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .animate-spin-slow {
    animation: spin-slow 2s linear infinite;
  }
</style>

<i class={`fa-solid fa-spinner ${size} ${color} ${speed}`}></i>
