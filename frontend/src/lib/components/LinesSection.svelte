<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import { BuiltWhenNear } from '$lib/dom/built-when-near.svelte';
	import { useScrollArea } from '$lib/dom/scroll-area';
	import { useReview } from '$lib/review/context';
	import type { DiffFile } from '$lib/types';
	import FileBody from './FileBody.svelte';
	import { type Extent, type FileView, roomOf } from './file-drawing.svelte';

	interface Props {
		/** What the section is known by among those its view draws. */
		sectionKey: string;
		/** The file it draws lines of, or the piece of one cut out for a story. */
		file: DiffFile;
		/** What its lines are highlighted and rendered as, if anything. */
		language: string | null;
		/** How its lines are drawn. */
		view: FileView;
		/** How much of the file it draws: the whole of it, or a piece cut out for a story. */
		extent: Extent;
		/** Whether its lines are folded away, its header left alone on the page. */
		folded: boolean;
		testId: string;
		/** How its header and lines are set among their neighbours: a rule under them, a frame around them. */
		class: ClassValue;
		/** What its view says before the header, inside the section: the number and reason of a story's step. */
		above?: Snippet | undefined;
		/** Its header, a `SectionHeader`: the file's name, and what its view says and offers beside it. */
		header: Snippet;
	}

	let { sectionKey, file, language, view, extent, folded, testId, class: framed, above, header }: Props = $props();
	const review = useReview();
	// The area its view scrolls in, which it comes near to be built: null while that is not drawn yet
	const scrollArea = useScrollArea();

	// What its lines will take up, so the browser can leave them undrawn off
	// screen, and its rows be built late, without what lies below moving as
	// they are: the stylesheet turns the counts into a height
	const room = $derived(roomOf(file, extent, view));

	let element: HTMLElement | undefined = $state();
	// Rows are built when the section comes within reach, and kept from then on
	const nearness = new BuiltWhenNear();

	$effect(() => (element ? review.sections.register(sectionKey, file.path, element) : undefined));
	$effect(() => (element ? nearness.watch(element, scrollArea()) : undefined));
</script>

<!-- A section of the page that draws lines of a file, whichever view draws it: it says where it is and
	which file it is of, holds the room its lines will take, and builds them once the reader comes near.
	Of what is drawn in it, its view says three things: what stands in its header, how its lines are
	drawn, and what stands above them. That last is inside the section: a reader taken to it reads from
	there -->
<section bind:this={element} data-testid={testId} data-path={file.path} class="cr-lines-section">
	{@render above?.()}
	<!-- The header and the lines in a frame of their own, which the header stays in sight within -->
	<div class={framed}>
		{@render header()}
		{#if !folded}
			<!-- The lines alone are left undrawn off screen, holding the room they are counted to take: the
				header is drawn always, so nothing has to guess how tall it is -->
			<div
				data-testid="file-lines"
				class="cr-file-lines"
				style:--cr-rows={room.rows}
				style:--cr-hunks={room.hunks}
				style:--cr-gaps={room.gaps}
				style:--cr-hunk-headers={room.hunkHeaders}
			>
				{#if nearness.built}
					<FileBody {file} {language} {view} {extent} />
				{:else}
					<div data-testid="file-placeholder" class="cr-file-placeholder"></div>
				{/if}
			</div>
		{/if}
	</div>
</section>
