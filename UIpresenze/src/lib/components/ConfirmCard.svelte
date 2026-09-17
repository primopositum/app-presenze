<script lang="ts">
  export let title: string = 'Conferma';
  export let message: string = 'Confermi questa operazione?';
  export let confirmLabel: string = 'Conferma';
  export let onConfirm: () => void;
  export let onCancel: () => void;
</script>

<div class="card">
  <div class="card2">
    <div class="form confirm-card">
      <div class="header">
        <span class="title">
          <i class="fa-solid fa-circle-question"></i>
          {title}
        </span>

        <button class="close-btn" on:click={onCancel} aria-label="Chiudi">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <div class="field confirm-field">
        <i class="fa-solid fa-circle-info input-icon-fa confirm-icon"></i>
        <span class="confirm-text-display">
          {message}
        </span>
      </div>

      <div class="actions">
        <button class="confirm-btn" on:click={onConfirm} type="button">
          {confirmLabel}
        </button>
      </div>
    </div>
  </div>
</div>

<style>
  @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css');

  .card {
    background-image: linear-gradient(163deg, #f59e0b 0%, #f97316 100%);
    border-radius: 22px;
    transition: all 0.3s;
    width: 100%;
    max-width: 350px;
    overflow: hidden;
  }

  .card:hover {
    box-shadow: 0px 0px 30px 1px rgba(245, 158, 11, 0.45);
  }

  .card2 {
    border-radius: 20px;
    background-color: #171717;
    transition: all 0.2s;
  }

  .card2:hover {
    transform: scale(0.98);
  }

  .form {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 1.8em;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .title {
    color: #f59e0b;
    font-size: 1.1em;
    font-weight: bold;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .close-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: #f59e0b;
    font-size: 1.2em;
    transition: 0.2s;
  }

  .close-btn:hover {
    color: #ffffff;
    transform: scale(1.1);
  }

  .field {
    display: flex;
    align-items: center;
    gap: 12px;
    border-radius: 25px;
    padding: 0.9em 1.2em;
    background-color: #171717;
    box-shadow: inset 2px 5px 10px rgb(28, 16, 0);
    min-width: 0;
  }

  .input-icon-fa {
    width: 20px;
    text-align: center;
  }

  .confirm-icon {
    color: #f59e0b;
    font-size: 1.2em;
  }

  .confirm-text-display {
    color: #fed7aa;
    font-size: 0.9em;
    line-height: 1.4;
    min-width: 0;
    max-width: 100%;
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
  }

  .confirm-btn {
    border: 1px solid #ea580c;
    background: #f97316;
    color: #ffffff;
    border-radius: 10px;
    padding: 0.5em 0.9em;
    font-weight: 700;
    cursor: pointer;
  }

  .confirm-btn:hover {
    background: #ea580c;
  }

  @media (max-width: 520px) {
    .form {
      padding: 1.2em;
      gap: 12px;
    }

    .field {
      flex-direction: column;
      align-items: flex-start;
    }

    .confirm-text-display {
      font-size: 0.85em;
    }
  }
</style>
