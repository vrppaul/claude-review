<script lang="ts">
	import { PageWatcher, sameFrame, type Frame } from '$lib/guide/spotlight';

	interface Props {
		/** What to light, by `data-tour` name. */
		targets: string[];
	}

	let { targets }: Props = $props();

	// How long the light takes to glide to a new step. Handed to the CSS as
	// --cr-guide-glide, so the two cannot disagree.
	const GLIDE_MS = 420;

	let frame = $state<Frame | null>(null);
	// The last frame drawn, kept apart from the state: reading the state while
	// the watcher reports would make the watcher depend on what it writes, and
	// rebuild itself on every move.
	let drawn: Frame | null = null;
	// Gliding only between steps: while the page scrolls under one, the light
	// keeps to what it lights rather than trailing behind it
	let gliding = $state(false);

	function follow(next: Frame | null) {
		if (sameFrame(drawn, next)) return;
		drawn = next;
		frame = next;
	}

	$effect(() => {
		const watcher = new PageWatcher(targets, follow);
		return () => watcher.stop();
	});

	$effect(() => {
		void targets;
		gliding = true;
		const settled = setTimeout(() => (gliding = false), GLIDE_MS);
		return () => clearTimeout(settled);
	});
</script>

{#if frame}
	<div
		data-testid="tour-spotlight"
		class="cr-guide-spot {gliding ? 'cr-guide-spot-gliding' : ''}"
		aria-hidden="true"
		style="left: {frame.left}px; top: {frame.top}px; width: {frame.width}px; height: {frame.height}px; --cr-guide-glide: {GLIDE_MS}ms"
	></div>
{/if}
