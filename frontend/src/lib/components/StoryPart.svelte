<script lang="ts" module>
	import { createAttachmentKey, type Attachment } from 'svelte/attachments';

	// How the heading of a part is made known to it, as part of what the heading is given to carry
	const HELD_AS_HEADING = createAttachmentKey();

	/** What the heading of a part carries: spread on it, it is what the part is named by, and says where it is. */
	type HeadingProps = { id: string } & Record<symbol, Attachment<HTMLElement>>;
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import { whenReadThrough } from '$lib/dom/scroll';
	import { useScrollArea } from '$lib/dom/scroll-area';
	import { useReview } from '$lib/review/context';

	interface Props {
		/** What the part is known by among the parts of the story. */
		partKey: string;
		testId: string;
		/** How what it holds is laid out. */
		class: ClassValue;
		/**
		 * What it begins with, drawn by whoever draws the part: what the change is called, a chapter's
		 * number and title. Its heading carries the props it is handed, and what that heading says is
		 * what the part is called to whoever goes through the page by its parts.
		 */
		head: Snippet<[HeadingProps]>;
		/** What it holds under its head. */
		children: Snippet;
	}

	let { partKey, testId, class: laidOut, head, children }: Props = $props();
	// What the part's heading is known by on the page, for the part to be named after it
	const headingId = $props.id();
	const review = useReview();
	// The area the story scrolls in: where the part's heading and its end come on screen
	const scrollArea = useScrollArea();

	let element: HTMLElement | undefined = $state();
	let heading: HTMLElement | undefined = $state();
	let endElement: HTMLElement | undefined = $state();

	const read = $derived(review.story.progress.isRead(partKey));

	const headingProps: HeadingProps = { id: headingId, [HELD_AS_HEADING]: holdHeading };

	/** The heading announces itself as it is drawn, and is let go as it goes. */
	function holdHeading(drawn: HTMLElement): () => void {
		heading = drawn;
		return () => (heading = undefined);
	}

	$effect(() => (element && heading ? review.parts.register(partKey, element, heading) : undefined));
	// Watched until the reader has read it through, and again once that is forgotten
	$effect(() =>
		read || !endElement
			? undefined
			: whenReadThrough(endElement, scrollArea(), () => review.story.progress.markRead(partKey))
	);
</script>

<!-- A part of the story with a place among its contents: its overview, a chapter, what it leaves out.
	It says where it and its heading are, so the page can say which part is being read and how deep in
	it the reader is, and take them to its head; and says when the reader has read it through. A press
	on its words puts the keyboard on nothing; its heading holds the keyboard when a bar that goes hands
	it on, until the keyboard leaves it. Placed, so that its end is its own foot. It is named by its
	heading, so what it is called is said once to whoever cannot see it, by the heading -->
<section bind:this={element} data-testid={testId} aria-labelledby={headingId} class={['relative', laidOut]}>
	{@render head(headingProps)}
	{@render children()}
	<!-- Where it ends: a mark of no height along its foot, out of the flow, so it takes no room in the part -->
	<div bind:this={endElement} data-testid="part-end" class="absolute inset-x-0 bottom-0"></div>
</section>
