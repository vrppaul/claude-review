<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import { BuiltWhenNear } from '$lib/dom/built-when-near.svelte';
	import { useScrollArea } from '$lib/dom/scroll-area';
	import { useReview } from '$lib/review/context';
	import type { DiffFile } from '$lib/types';

	interface Props {
		/** What the section is known by among those its view draws. */
		sectionKey: string;
		/** The file it draws lines of, or the piece of one cut out for a story. */
		file: DiffFile;
		/** Whether its lines are folded away, its header left alone on the page. */
		folded: boolean;
		testId: string;
		/** How its header and lines are set among their neighbours: a rule under them, a frame around them. */
		class: ClassValue;
		/** What its view says before the header, inside the section: the number and reason of a story's step. */
		above?: Snippet | undefined;
		/** Its header, a `SectionHeader`: the file's name, and what its view says and offers beside it. */
		header: Snippet;
		/** Its lines, asked for once the reader has come near, and not while they are folded away. */
		lines: Snippet;
	}

	let { sectionKey, file, folded, testId, class: framed, above, header, lines }: Props = $props();
	const review = useReview();
	// The area its view scrolls in, which it comes near to be built: null while that is not drawn yet
	const scrollArea = useScrollArea();

	// How many rows it will draw, so the browser can leave it undrawn off
	// screen without the scrollbar lurching once it is drawn for real: the
	// stylesheet turns the count into a height. At least one, unless folded.
	const rowCount = $derived(file.hunks.reduce((count, hunk) => count + hunk.lines.length, 0));
	const rowsDrawn = $derived(folded ? 0 : Math.max(rowCount, 1));

	let element: HTMLElement | undefined = $state();
	// Rows are built when the section comes within reach, and kept from then on
	const nearness = new BuiltWhenNear();

	$effect(() => (element ? review.sections.register(sectionKey, file.path, element) : undefined));
	$effect(() => (element ? nearness.watch(element, scrollArea()) : undefined));
</script>

<!-- A section of the page that draws lines of a file, whichever view draws it: it says where it is and
	which file it is of, holds the room its rows will take, and builds them once the reader comes near.
	Of what is drawn in it, its view says three things: what stands in its header, what its lines are,
	and what stands above them. That last is inside the section: a reader taken to it reads from there -->
<section
	bind:this={element}
	data-testid={testId}
	data-path={file.path}
	class="cr-lines-section"
	style:--cr-rows={rowsDrawn}
>
	{@render above?.()}
	<!-- The header and the lines in a frame of their own: what is left undrawn off screen, and what the
		header stays in sight within -->
	<div class={['cr-file-frame', framed]}>
		{@render header()}
		{#if !folded}
			{#if nearness.built}
				{@render lines()}
			{:else}
				<div data-testid="file-placeholder" class="cr-file-placeholder"></div>
			{/if}
		{/if}
	</div>
</section>
