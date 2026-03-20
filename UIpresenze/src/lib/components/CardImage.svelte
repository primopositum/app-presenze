<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let imageSrc: string;
	export let caption: string;
	export let alt: string = '';
	export let href: string | null = null;
	export let className: string = '';

	const dispatch = createEventDispatcher();

	function handleClick(event: MouseEvent) {
		// Se c'è un href, lascia che il link funzioni normalmente
		if (!href) {
			dispatch('click', event);
		}
	}

	function handleKeyDown(event: KeyboardEvent) {
		// Supporto per accessibilità: attiva click con Enter o Space
		if (!href && (event.key === 'Enter' || event.key === ' ')) {
			event.preventDefault();
			dispatch('click', event);
		}
	}
</script>

<div>
	<svelte:element
		this={href ? 'a' : 'div'}
		href={href}
		class="block overflow-hidden cursor-pointer"
		on:click={handleClick}
		on:keydown={handleKeyDown}
		role={href ? undefined : 'button'}
		tabindex={href ? undefined : 0}
		{...$$restProps}
	>
		<img
			src={imageSrc}
			alt={alt}
			class={`object-cover transition-all duration-500 ease-in-out hover:scale-110 ${className}`}
		/>
	</svelte:element>
	<div class="p-4">
		<p class="text-sm text-gray-600 text-center">{caption}</p>
	</div>
</div>