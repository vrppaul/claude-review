<script lang="ts">
	import type { Snippet } from 'svelte';
	import { useReview } from '$lib/review/context';
	import Icon from '$lib/ui/Icon.svelte';
	import Row from '$lib/ui/Row.svelte';
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

<!-- The entry's node on the axis, ringed in the reader's mark while its part is being read -->
{#snippet onTheAxis()}
	<span
		aria-hidden="true"
		data-testid="part-node"
		class={[
			'cr-contents-node',
			checked && 'cr-contents-node-read',
			changed && 'cr-contents-node-changed',
			beingRead && 'cr-contents-node-current'
		]}
	>
		{#if checked}
			<Icon name="check" size="xs" testId="part-read-mark" />
		{:else}
			{@render node()}
		{/if}
	</span>
{/snippet}

<!-- Threads hang in the part: how many, at the row's far end, as the tree of files says of a file; said in the
	entry's name to whoever cannot see it -->
{#snippet threadsInIt()}
	{#if threads > 0}
		<span data-testid="part-threads" aria-hidden="true" class="badge badge-xs badge-primary">{threads}</span>
	{/if}
{/snippet}

<!-- An entry of a story's contents: a node on the axis and the part's title, one press to its head, a row as
	the tree's are. A part above the one being read steps back, in faint words as a file the reader has finished
	with does, a check in its node and its stretch of the axis in the colour of what is done. A chapter a round
	changed code of after it was told rings its number in the warning's colour in place of the check, scrolled
	past or not. The node is for the eye; the entry's name says whether the part is scrolled past in words. A title
	longer than the row is wide wraps onto more lines and reads whole -->
<li data-testid="contents-entry" class={['cr-contents-entry', read && 'cr-contents-entry-read']}>
	<Row
		names="title"
		testId="go-to-part"
		viewed={read}
		aria-label={threads > 0 ? calledWithThreads(called, threads) : called}
		aria-current={beingRead ? 'location' : undefined}
		onclick={() => review.parts.goTo(part)}
		leading={onTheAxis}
		trailing={threadsInIt}
	>
		{#snippet label()}
			{title}
		{/snippet}
	</Row>
	{@render children?.()}
</li>
