<script lang="ts">
	import type { Snippet } from 'svelte';
	import { useReview } from '$lib/review/context';
	import Icon from './Icon.svelte';
	import { calledOnceRead, calledWithThreads } from './story-words';

	interface Props {
		/** What the part of the story it leads to is known by. */
		part: string;
		/** What it is called in full, to whoever cannot see its node: "Overview", "Chapter 2: The end". */
		label: string;
		/** What it says beside its node: the part's title. */
		title: string;
		/** What stands in its node until the part is read through: a chapter's number, the overview's dot. */
		node: Snippet;
		/** How many threads hang in the part: on its words, or on the lines of its pieces. */
		threads: number;
		/** Whether a round changed the code of any of its steps after the story was told: a chapter's alone can be. */
		changed?: boolean;
		/** What hangs under it: the files a chapter tells. */
		children?: Snippet;
	}

	let { part, label, title, node, threads, changed = false, children }: Props = $props();
	const review = useReview();

	const beingRead = $derived(review.parts.beingRead === part);
	const read = $derived(review.partsScrolledPast.has(part));
	// Scrolled past, its node holds a check, unless a step changed since: then it holds what it held before
	const checked = $derived(read && !changed);
	// What the entry is called, with whether its part is scrolled past; its name adds how many threads hang there
	const called = $derived(read ? calledOnceRead(label) : label);
</script>

<!-- An entry of a story's contents: a node on the axis and the part's title, one press to its head.
	A part above the one being read steps back, a check in its node and its stretch of the axis in the
	colour of what is done. A chapter a round changed code of after it was told rings its number in the
	warning's colour in place of the check, scrolled past or not. The node is for the eye; the entry's
	name says whether the part is scrolled past in words -->
<li data-testid="contents-entry" class={['cr-contents-entry', read && 'cr-contents-entry-read']}>
	<button
		type="button"
		data-testid="go-to-part"
		class={['cr-contents-row', read && 'cr-muted']}
		aria-label={threads > 0 ? calledWithThreads(called, threads) : called}
		aria-current={beingRead ? 'location' : undefined}
		onclick={() => review.parts.goTo(part)}
	>
		<span
			aria-hidden="true"
			class={[
				'cr-contents-node',
				checked && 'cr-contents-node-read',
				changed && 'cr-contents-node-changed',
				beingRead && 'cr-contents-node-current'
			]}
		>
			{#if checked}
				<Icon name="check" data-testid="part-read-mark" class="h-2.5 w-2.5" />
			{:else}
				{@render node()}
			{/if}
		</span>
		<span class="min-w-0">{title}</span>
		{#if threads > 0}
			<!-- A thread hangs in the part: a dot at the row's far end, its count said in the entry's name -->
			<span data-testid="part-threads" aria-hidden="true" class="cr-contents-dot cr-contents-threads"></span>
		{/if}
	</button>
	{@render children?.()}
</li>
