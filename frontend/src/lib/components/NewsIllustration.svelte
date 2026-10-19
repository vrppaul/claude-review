<script lang="ts">
	import type { Component } from 'svelte';
	import type { DrawingName, Illustration } from '$lib/guide/news';
	import Picture from '$lib/ui/Picture.svelte';
	import PastedScreenshot from './PastedScreenshot.svelte';
	import StorySketch from './StorySketch.svelte';

	interface Props {
		illustration: Illustration;
	}

	let { illustration }: Props = $props();

	// Every drawing an entry can name; a name missing here does not type-check
	const DRAWINGS: Record<DrawingName, Component> = {
		'pasted-screenshot': PastedScreenshot,
		'story-sketch': StorySketch
	};
</script>

{#if illustration.kind === 'image'}
	<Picture src={illustration.src} alt={illustration.alt} testId="news-image" />
{:else if illustration.kind === 'drawing'}
	{@const Drawing = DRAWINGS[illustration.name]}
	<Drawing />
{/if}
