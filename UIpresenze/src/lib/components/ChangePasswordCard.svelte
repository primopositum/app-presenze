<script lang="ts">
  import ErrorCard from '$lib/components/ErrorCard.svelte';
  import { changePassword } from '$lib/services/users';

  export let onSuccess: ((message: string) => void) | null = null;

  let showOldPassword = false;
  let showNewPassword = false;
  let showConfirmPassword = false;
  
  let oldPassword = '';
  let newPassword = '';
  let confirmPassword = '';
  
  let loading = false;
  let error: string | null = null;

  const toggleOldPassword = () => (showOldPassword = !showOldPassword);
  const toggleNewPassword = () => (showNewPassword = !showNewPassword);
  const toggleConfirmPassword = () => (showConfirmPassword = !showConfirmPassword);

  // Reattività per controllare se le password coincidono
  $: passwordsMatch = newPassword === confirmPassword;
  $: canSubmit = newPassword.length > 0 && confirmPassword.length > 0 && passwordsMatch && !loading;

  async function submit(event: Event) {
    event.preventDefault();
    
    if (!passwordsMatch) {
      error = "Le password non coincidono";
      return;
    }

    error = null;
    loading = true;
    try {
      await changePassword({ old_password: oldPassword, new_password: newPassword });
      oldPassword = '';
      newPassword = '';
      confirmPassword = '';
      onSuccess?.('Password cambiata con successo');
    } catch (err: any) {
      error = err?.message || 'Errore imprevisto';
    } finally {
      loading = false;
    }
  }
</script>

<div class="form-container">
  <form class="form" on:submit={submit}>
    <span class="heading">Change password</span>

    {#if error}
      <ErrorCard message={error} onClose={() => (error = null)} />
    {/if}

    <div class="form-group">
      <input
        class="form-input"
        required
        type={showOldPassword ? 'text' : 'password'}
        bind:value={oldPassword}
        autocomplete="current-password"
      />
      <label>old password</label>
      <button
        type="button"
        class="toggle-btn"
        on:click={toggleOldPassword}
        aria-label={showOldPassword ? 'Nascondi password' : 'Mostra password'}
      >
        {#if showOldPassword}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" class="icon" viewBox="0 0 24 24" stroke-width="2">
            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12Z" />
            <path d="M4 4 20 20" />
          </svg>
        {:else}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" class="icon" viewBox="0 0 24 24" stroke-width="2">
            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        {/if}
      </button>
    </div>

    <div class="form-group">
      <input
        class="form-input"
        required
        type={showNewPassword ? 'text' : 'password'}
        bind:value={newPassword}
        autocomplete="new-password"
      />
      <label>new password</label>
      <button
        type="button"
        class="toggle-btn"
        on:click={toggleNewPassword}
        aria-label={showNewPassword ? 'Nascondi password' : 'Mostra password'}
      >
        {#if showNewPassword}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" class="icon" viewBox="0 0 24 24" stroke-width="2">
            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12Z" />
            <path d="M4 4 20 20" />
          </svg>
        {:else}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" class="icon" viewBox="0 0 24 24" stroke-width="2">
            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        {/if}
      </button>
    </div>

    <div class="form-group">
      <input
        class="form-input {confirmPassword && !passwordsMatch ? 'input-error' : ''}"
        required
        type={showConfirmPassword ? 'text' : 'password'}
        bind:value={confirmPassword}
      />
      <label>confirm password</label>
      <button
        type="button"
        class="toggle-btn"
        on:click={toggleConfirmPassword}
        aria-label={showConfirmPassword ? 'Nascondi password' : 'Mostra password'}
      >
        {#if showConfirmPassword}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" class="icon" viewBox="0 0 24 24" stroke-width="2">
            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12Z" />
            <path d="M4 4 20 20" />
          </svg>
        {:else}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" class="icon" viewBox="0 0 24 24" stroke-width="2">
            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        {/if}
      </button>
      {#if confirmPassword && !passwordsMatch}
        <span class="error-text">Le password non coincidono</span>
      {/if}
    </div>

    <button type="submit" disabled={!canSubmit}>
      {loading ? 'SALVATAGGIO...' : 'CHANGE'}
    </button>
  </form>
</div>

<style>
  .form-container {
    background: linear-gradient(#212121, #212121) padding-box,
      linear-gradient(120deg, transparent 25%, #1cb0ff, #40ff99) border-box;
    border: 2px solid transparent;
    padding: 32px 24px;
    font-size: 14px;
    color: white;
    display: flex;
    flex-direction: column;
    gap: 20px;
    box-sizing: border-box;
    border-radius: 16px;
  }

  .form {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }

  .heading {
    font-size: 20px;
    font-weight: 600;
  }

  .form-input {
    color: white;
    background: transparent;
    border: 1px solid #414141;
    border-radius: 5px;
    padding: 8px 36px 8px 8px;
    outline: none;
    width: 100%;
    box-sizing: border-box;
  }

  .input-error {
    border-color: #ff4444 !important;
  }

  .error-text {
    color: #ff4444;
    font-size: 11px;
    margin-top: 2px;
  }

  button[type="submit"] {
    border-radius: 5px;
    padding: 10px 24px;
    background: #ffffff14;
    color: #c7c5c5;
    border: 1px solid #414141;
    width: 100%;
    font-weight: bold;
    transition: all 0.3s;
  }

  button[type="submit"]:hover:not(:disabled) {
    background: #ffffff20;
    color: white;
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
    color: #414141;
    position: relative;
    width: 100%;
  }

  .toggle-btn {
    position: absolute;
    right: 6px;
    top: 6px;
    width: 28px;
    height: 28px;
    border: 0;
    background: transparent;
    color: #bdb8b8;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    z-index: 2;
  }

  .toggle-btn:hover {
    background: #2a2a2a;
    cursor: pointer;
  }

  .icon {
    width: 18px;
    height: 18px;
  }

  .form-group label {
    position: absolute;
    top: 8px;
    left: 8px;
    padding: 0 5px;
    pointer-events: none;
    transition: 0.5s;
    color: #888;
  }

  .form-group input:focus ~ label,
  .form-group input:valid ~ label {
    top: -10px;
    left: 5px;
    background: #212121;
    color: #1cb0ff;
    font-size: 12px;
  }
</style>