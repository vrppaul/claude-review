<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorLabel } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { raisedByAgent } from '$lib/utils/speakers';
	import { counted } from '$lib/utils/words';
	import FoldToggle from './FoldToggle.svelte';
	import Icon from './Icon.svelte';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();

	const unread = $derived(review.threads.reading.isUnread(thread.id));
</script>

<!-- Folded, by hand or by settling it: one line, and the first words of what
	was said. Either way it opens to be read. -->
<div
	data-testid={thread.resolved ? 'resolved-thread' : 'folded-thread'}
	class={[
		'flex max-w-[96ch] items-center gap-3 rounded-r px-4 py-2',
		thread.resolved ? 'cr-resolved' : 'cr-folded',
		!thread.resolved && raisedByAgent(thread) && 'cr-raised'
	]}
>
	{#if thread.resolved}
		<Icon name="check" class="h-3 w-3 shrink-0 text-(--cr-add-edge)" />
	{/if}
	<FoldToggle
		folded
		subject="this thread"
		testId="fold-comment"
		onToggle={() => review.threads.reading.setFolded(thread.id, false)}
	/>
	<button
		type="button"
		data-testid="unfold-thread"
		class="flex min-w-0 flex-1 items-baseline gap-3 text-left"
		onclick={() => review.threads.reading.setFolded(thread.id, false)}
	>
		<span class="cr-comment-ref shrink-0 font-mono text-xs">{anchorLabel(thread.anchor)}</span>
		<span class="cr-muted truncate text-sm">{thread.body || 'an image'}</span>
		{#if thread.turns.length > 0}
			<span class="cr-faint shrink-0 text-xs">{counted(thread.turns.length, 'turn', 'turns')}</span>
		{/if}
	</button>
	{#if unread}
		<span class="shrink-0 text-xs text-(--cr-mark)"><span aria-hidden="true">●</span> new reply</span>
	{/if}
	{#if thread.resolved}
		<button
			type="button"
			data-testid="reopen-thread"
			class="btn btn-ghost btn-xs"
			onclick={() => review.threads.setResolved(thread.id, false)}
		>
			Reopen
		</button>
	{/if}
</div>
