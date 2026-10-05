<script lang="ts">
	import type { Component } from 'svelte';
	import type { DrawingName, Illustration } from '$lib/guide/news';
	import PastedScreenshot from './PastedScreenshot.svelte';

	interface Props {
		illustration: Illustration;
	}

	let { illustration }: Props = $props();

	// Every drawing an entry can name; a name missing here does not type-check
	const DRAWINGS: Record<DrawingName, Component> = {
		'pasted-screenshot': PastedScreenshot
	};
</script>

{#if illustration.kind === 'image'}
	<img data-testid="news-image" class="cr-news-image" src={illustration.src} alt={illustration.alt} />
{:else}
	{@const Drawing = DRAWINGS[illustration.name]}
	<Drawing />
{/if}
