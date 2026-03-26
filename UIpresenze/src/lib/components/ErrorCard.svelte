<script lang="ts">
  export let message: string = 'Si è verificato un errore imprevisto.';
  export let onClose: () => void;
</script>

<div class="card">
  <div class="card2">
    <div class="form error-card">

      <!-- Header -->
      <div class="header">
        <span class="title">
          <i class="fa-solid fa-triangle-exclamation"></i>
          Errore
        </span>

        <button class="close-btn" on:click={onClose} aria-label="Chiudi">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <!-- Error message -->
      <div class="field error-field">
        <i class="fa-solid fa-circle-xmark input-icon-fa error-icon"></i>
        <span class="error-text-display">
          {message}
        </span>
      </div>

    </div>
  </div>
</div>

<style>
  @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css');

  /* CARD BASE */
  .card {
    background-image: linear-gradient(163deg, #ff4d4d 0%, #ff005d 100%);
    border-radius: 22px;
    transition: all 0.3s;
    width: 100%;
    max-width: 350px;
    overflow: hidden;
  }

  .card:hover {
    box-shadow: 0px 0px 30px 1px rgba(255, 77, 77, 0.45);
  }

  .card2 {
    border-radius: 20px;
    background-color: #171717;
    transition: all 0.2s;
  }

  .card2:hover {
    transform: scale(0.98);
  }

  /* CONTENT */
  .form {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 1.8em;
  }

  /* HEADER */
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .title {
    color: #ff4d4d;
    font-size: 1.1em;
    font-weight: bold;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* CLOSE BUTTON */
  .close-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: #ff4d4d;
    font-size: 1.2em;
    transition: 0.2s;
  }

  .close-btn:hover {
    color: #ffffff;
    transform: scale(1.1);
  }

  /* ERROR FIELD */
  .field {
    display: flex;
    align-items: center;
    gap: 12px;
    border-radius: 25px;
    padding: 0.9em 1.2em;
    background-color: #171717;
    box-shadow: inset 2px 5px 10px rgb(20, 0, 0);
    min-width: 0;
  }

  .input-icon-fa {
    width: 20px;
    text-align: center;
  }

  .error-icon {
    color: #ff4d4d;
    font-size: 1.2em;
  }

  .error-text-display {
    color: #ffb3b3;
    font-size: 0.9em;
    line-height: 1.4;
    min-width: 0;
    max-width: 100%;
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
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

    .error-text-display {
      font-size: 0.85em;
    }
  }
</style>
