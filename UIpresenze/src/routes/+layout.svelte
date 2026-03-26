<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import '../app.css'; 
	import { onMount } from 'svelte';
	import { auth } from '$lib/stores/auth';
	import { startAutoRefresh, stopAutoRefresh } from '$lib/api';
	import { goto } from '$app/navigation';

	export const prerender = false;
	export const ssr = false;
	// Inizializzazione
	onMount(() => {
		// Auth
		auth.init();
		if (!$auth.isAuthed) {
			stopAutoRefresh();
			goto('/login');
			return;
		}
		startAutoRefresh();
	});
</script>

<!-- HEADER -->
{#if $auth.isAuthed}
	<Header />
{/if}

<!-- CONTENUTO PRINCIPALE -->
<main class="p-4 max-w-7xl mx-auto">
	<slot/>
</main>
