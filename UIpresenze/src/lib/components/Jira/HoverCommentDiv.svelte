<script lang="ts">
  export let comments: string[] = [];
  export let label = 'Dettagli';

  type ParsedComment = {
    author: string;
    text: string;
  };

  let parsedComments: ParsedComment[] = [];
  let authorColors: Record<string, string> = {};

  function randomAuthorColor() {
    const h = Math.floor(Math.random() * 360);
    return `hsl(${h} 72% 93%)`;
  }

  function parseComment(value: string): ParsedComment {
    const safe = String(value || '').trim();
    const idx = safe.indexOf(':');
    if (idx > 0) {
      const left = safe.slice(0, idx).trim();
      const right = safe.slice(idx + 1).trim();
      if (left && right) {
        return { author: left, text: right };
      }
    }
    return { author: 'Sistema', text: safe };
  }

  $: parsedComments = comments.map(parseComment).filter((c) => c.text);
  $: {
    const next: Record<string, string> = {};
    for (const c of parsedComments) {
      if (!next[c.author]) {
        next[c.author] = randomAuthorColor();
      }
    }
    authorColors = next;
  }
</script>

<div class="hover-comments">
  <button class="trigger" type="button" aria-label={label} title={label} on:click|stopPropagation>
    <span class="dot"></span>
    <span class="dot"></span>
    <span class="dot"></span>
  </button>

  <div class="panel" role="tooltip">
    {#if comments.length === 0}
      <p class="empty">Nessun commento</p>
    {:else}
      <ul>
        {#each parsedComments as c, i}
          <li style={`--comment-author-color:${authorColors[c.author] || '#f8fafc'};`}>
            <strong>{c.author}</strong>
            <span>{c.text}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

<style>
  .hover-comments {
    position: relative;
    display: inline-flex;
    flex-shrink: 0;
    z-index: 90;
  }

  .trigger {
    width: 34px;
    height: 18px;
    border-radius: 999px;
    border: 1px solid #cbd5e1;
    background: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 3px;
    padding: 0 6px;
    cursor: pointer;
    transition: border-color 0.15s ease, background 0.15s ease;
  }
  .trigger:hover {
    border-color: #94a3b8;
    background: #f8fafc;
  }
  .dot {
    width: 3px;
    height: 3px;
    border-radius: 999px;
    background: #64748b;
  }

  .panel {
    position: absolute;
    right: 0;
    top: calc(100% + 6px);
    width: 220px;
    max-height: 160px;
    overflow: auto;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #fff;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.14);
    padding: 8px;
    opacity: 0;
    transform: translateY(-4px);
    pointer-events: none;
    transition: opacity 0.12s ease, transform 0.12s ease;
    z-index: 1200;
  }
  .hover-comments:hover .panel,
  .hover-comments:focus-within .panel {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
  }

  ul {
    margin: 0;
    padding: 0;
    list-style: none;
    display: grid;
    gap: 6px;
  }
  li {
    font-size: 11px;
    color: #334155;
    line-height: 1.3;
    font-family: var(--font-mono);
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 5px 6px;
    background: var(--comment-author-color, #f8fafc);
    display: grid;
    gap: 2px;
  }
  li strong {
    font-size: 10px;
    color: #0f172a;
    letter-spacing: 0.01em;
  }
  li span {
    color: #334155;
  }
  .empty {
    margin: 0;
    font-size: 11px;
    color: #64748b;
    font-family: var(--font-mono);
  }
</style>
