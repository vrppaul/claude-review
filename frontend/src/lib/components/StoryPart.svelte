<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import { useReview } from '$lib/review/context';

	interface Props {
		/** What the part is known by among the parts of the story. */
		partKey: string;
		/** What it is called to whoever goes through the page by its parts: "Overview", "Chapter 2: The end". */
		label: string;
		testId: string;
		/** How what it holds is laid out. */
		class: ClassValue;
		children: Snippet;
	}

	let { partKey, label, testId, class: laidOut, children }: Props = $props();
	const review = useReview();

	let element: HTMLElement | undefined = $state();

	$effect(() => (element ? review.parts.register(partKey, element) : undefined));
</script>

<!-- A part of the story with a place among its contents: its overview, a chapter, what it leaves out.
	It says where it is, so the page can say which part is being read and take the reader to its head -->
<section bind:this={element} data-testid={testId} aria-label={label} class={laidOut}>
	{@render children()}
</section>
