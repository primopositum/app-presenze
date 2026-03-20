<script lang="ts">
  import { initTimeEntryFormContext } from '$lib/context/timeEntryForm';
  import TimeEntryFormModal from '$lib/components/ctx/TimeEntryFormModal.svelte';

  initTimeEntryFormContext();
</script>

<slot />
<TimeEntryFormModal />
