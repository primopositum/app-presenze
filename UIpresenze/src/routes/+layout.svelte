<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import '../app.css'; 
	import { onMount } from 'svelte';
	import { auth } from '$lib/stores/auth';
	import { jiraControl, ensureJiraControlLoaded, isJiraRoute, resetJiraControl } from '$lib/stores/jiraControl';
	import { startAutoRefresh, stopAutoRefresh } from '$lib/api';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	export const prerender = false;
	export const ssr = false;
	// Inizializzazione
	onMount(() => {
		// Auth
		auth.init();
		if (!$auth.isAuthed) {
			resetJiraControl();
			stopAutoRefresh();
			goto('/login');
			return;
		}
		startAutoRefresh();
		void ensureJiraControlLoaded();
	});

	$: if ($auth.isAuthed && isJiraRoute($page.url.pathname) && $jiraControl.loaded && !$jiraControl.enabled) {
		goto('/', { replaceState: true });
	}

	$: if ($auth.isAuthed && !$jiraControl.loaded && !$jiraControl.loading) {
		void ensureJiraControlLoaded();
	}

	$: if (!$auth.isAuthed && $jiraControl.loaded) {
		resetJiraControl();
	}
</script>

<!-- HEADER -->
{#if $auth.isAuthed}
	<Header />
{/if}

<!-- CONTENUTO PRINCIPALE -->
<main class="layout-shell">
	<slot/>
</main>

<style>
	.layout-shell {
		width: 80%;
		max-width: 80%;
		margin: 0 auto;
		padding: 1rem;
	}

	@media (max-width: 900px) {
		.layout-shell {
			width: 100%;
			max-width: 100%;
			padding: 0.75rem;
		}
	}
</style>
