<script lang="ts">
  export let message = '';
  export let deleting = false;
  export let onCancel: () => void;
  export let onConfirm: () => void | Promise<void>;
</script>

<div class="card" role="dialog" aria-modal="true" aria-labelledby="delete-confirm-title" tabindex="-1">
  <div class="card2">
    <div class="form">
      <div class="header">
        <span id="delete-confirm-title" class="title">
          <i class="fa-solid fa-triangle-exclamation"></i>
          Conferma eliminazione
        </span>
        <button class="close-btn" type="button" on:click={onCancel} disabled={deleting} aria-label="Chiudi">×</button>
      </div>

      <p class="message">{message}</p>

      <div class="actions">
        <button class="cancel-btn" type="button" on:click={onCancel} disabled={deleting}>Annulla</button>
        <button class="delete-btn" type="button" on:click={onConfirm} disabled={deleting}>
          {deleting ? 'Eliminazione...' : 'Elimina'}
        </button>
      </div>
    </div>
  </div>
</div>

<style>
  @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css');

  .card { width: min(100%, 390px); overflow: hidden; border-radius: 22px; background-image: linear-gradient(163deg, #ff4d4d 0%, #ff005d 100%); box-shadow: 0 18px 48px rgb(15 23 42 / .35); }
  .card2 { border-radius: 20px; background: #171717; }
  .form { display: grid; gap: 1rem; padding: 1.5rem; }
  .header, .actions { display: flex; align-items: center; justify-content: space-between; gap: .75rem; }
  .title { display: flex; align-items: center; gap: .5rem; color: #ff4d4d; font-size: 1rem; font-weight: 700; }
  .close-btn { flex: 0 0 auto; border: 0; background: transparent; color: #ff4d4d; font-size: 1.45rem; line-height: 1; cursor: pointer; }
  .message { margin: 0; padding: .9rem 1rem; border-radius: 14px; color: #ffb3b3; background: #171717; box-shadow: inset 2px 5px 10px rgb(20 0 0); font-size: .88rem; line-height: 1.45; overflow-wrap: anywhere; }
  .actions { justify-content: flex-end; flex-wrap: wrap; }
  .actions button { border: 0; border-radius: 8px; padding: .5rem .75rem; font: inherit; font-size: .82rem; font-weight: 700; cursor: pointer; }
  .cancel-btn { color: #e2e8f0; background: #334155; }
  .delete-btn { color: #fff; background: #dc2626; }
  button:disabled { cursor: not-allowed; opacity: .6; }

  @media (max-width: 480px) {
    .form { padding: 1.15rem; }
    .actions button { flex: 1 1 7rem; }
  }
</style>
