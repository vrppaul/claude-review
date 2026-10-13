<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import { whenReadThrough } from '$lib/dom/scroll';
	import { useScrollArea } from '$lib/dom/scroll-area';
	import { useReview } from '$lib/review/context';

	interface Props {
		/** What the part is known by among the parts of the story. */
		partKey: string;
		/** What it is called to whoever goes through the page by its parts: "Overview", "Chapter 2: The end". */
		label: string;
		testId: string;
		/** How what it holds is laid out. */
		class: ClassValue;
		/** What it begins with: what the change is called, a chapter's number and title. */
		head: Snippet;
		/** What it holds under its head. */
		children: Snippet;
	}

	let { partKey, label, testId, class: laidOut, head, children }: Props = $props();
	const review = useReview();
	// The area the story scrolls in: where the part's head and its end come on screen
	const scrollArea = useScrollArea();

	let element: HTMLElement | undefined = $state();
	let headElement: HTMLElement | undefined = $state();
	let endElement: HTMLElement | undefined = $state();

	const read = $derived(review.story.progress.isRead(partKey));

	$effect(() => (element ? review.parts.register(partKey, element) : undefined));
	// Watched until the reader has read it through, and again once that is forgotten
	$effect(() =>
		read || !headElement || !endElement
			? undefined
			: whenReadThrough(headElement, endElement, scrollArea(), () => review.story.progress.markRead(partKey))
	);
</script>

<!-- A part of the story with a place among its contents: its overview, a chapter, what it leaves out.
	It says where it is, so the page can say which part is being read and take the reader to its head,
	and says when the reader has read it through. Placed, so that its end is its own foot -->
<section bind:this={element} data-testid={testId} aria-label={label} class={['relative', laidOut]}>
	<!-- Its head in a box of its own, spaced as the part is: what heads it stands as it would among the rest -->
	<div bind:this={headElement} data-testid="part-head" class="flex flex-col gap-[inherit]">
		{@render head()}
	</div>
	{@render children()}
	<!-- Where it ends: a mark of no height along its foot, out of the flow, so it takes no room in the part -->
	<div bind:this={endElement} data-testid="part-end" class="absolute inset-x-0 bottom-0"></div>
</section>
