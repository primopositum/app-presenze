<div class="jira-history-hover-root">
  <slot />
</div>

<style>
  :global(.jira-history-hover-root [data-history-hover]),
  :global(.jira-history-hover-root button:not([data-history-hover-exclude])) {
    transition: background-color 0.15s ease;
  }

  :global(
    .jira-history-hover-root
      [data-history-hover]:not([data-history-hover-exclude]):hover:not(
        :has(
          [data-history-hover]:hover,
          [data-history-hover-exclude]:hover,
          button:hover
        )
      )
  ),
  :global(.jira-history-hover-root button:not([data-history-hover-exclude]):hover) {
    background-color: #fff7ed !important;
  }
</style>
