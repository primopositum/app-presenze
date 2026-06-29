<main class="business-layout">
  <slot />
</main>

<style>
  .business-layout {
    width: min(100%, 1867px);
    margin: 0 auto;
    padding: 0 1rem 2rem;
  }

  @media (max-width: 700px) {
    .business-layout {
      width: 100%;
      padding: 0 0.75rem 1.5rem;
    }
  }
</style>
