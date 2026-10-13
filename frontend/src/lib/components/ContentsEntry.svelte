<script lang="ts">
	import type { Snippet } from 'svelte';
	import { useReview } from '$lib/review/context';

	interface Props {
		/** What the part of the story it leads to is known by. */
		part: string;
		/** What it is called in full, to whoever cannot see its node: "Overview", "Chapter 2: The end". */
		label: string;
		/** What it says beside its node: the part's title. */
		title: string;
		/** What stands in its node: a chapter's number, the overview's dot. */
		node: Snippet;
		/** What hangs under it: the files a chapter tells. */
		children?: Snippet;
	}

	let { part, label, title, node, children }: Props = $props();
	const review = useReview();

	const beingRead = $derived(review.parts.beingRead === part);
</script>

<!-- An entry of a story's contents: a node on the axis and the part's title, one press to its head.
	The node is for the eye; the entry's name says the same in words -->
<li data-testid="contents-entry" class="cr-contents-entry">
	<button
		type="button"
		data-testid="go-to-part"
		class="cr-contents-row"
		aria-label={label}
		aria-current={beingRead ? 'location' : undefined}
		onclick={() => review.parts.goTo(part)}
	>
		<span aria-hidden="true" class={['cr-contents-node', beingRead && 'cr-contents-node-current']}>
			{@render node()}
		</span>
		<span class="min-w-0">{title}</span>
	</button>
	{@render children?.()}
</li>
