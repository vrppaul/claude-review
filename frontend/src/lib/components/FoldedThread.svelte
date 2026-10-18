<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorLabel } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { raisedByAgent } from '$lib/utils/speakers';
	import { plainWords } from '$lib/utils/plain-words';
	import { counted } from '$lib/utils/words';
	import FoldToggle from './FoldToggle.svelte';
	import Icon from './Icon.svelte';
	import NewReplyMark from './NewReplyMark.svelte';
	import ReopenButton from './ReopenButton.svelte';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();

	const unread = $derived(review.threads.reading.isUnread(thread.id));

	/** Open the thread again; the keyboard stays on its toggle, drawn anew at the head of the open thread. */
	function unfold() {
		review.threads.reading.setFolded(thread.id, false);
		review.sections.keyboardToThreadFold(thread.id);
	}
</script>

<!-- Folded, by hand or by settling it: one line as wide as the card it folds, and the first words of what
	was said. Either way it opens to be read, by the chevron where the open card has it, at the far end -->
<div
	data-testid={thread.resolved ? 'resolved-thread' : 'folded-thread'}
	class={[
		'flex items-center gap-3 rounded-r px-4 py-2',
		thread.resolved ? 'cr-resolved' : 'cr-folded',
		!thread.resolved && raisedByAgent(thread) && 'cr-raised'
	]}
>
	{#if thread.resolved}
		<Icon name="check" class="h-3 w-3 shrink-0 text-(--cr-done)" />
	{/if}
	<button
		type="button"
		data-testid="unfold-thread"
		class="flex min-w-0 flex-1 items-baseline gap-3 text-left"
		onclick={unfold}
	>
		<span class="cr-comment-ref shrink-0 font-mono text-xs">{anchorLabel(thread.anchor)}</span>
		<span class="cr-muted truncate text-sm">{plainWords(thread.body) || 'an image'}</span>
		{#if thread.turns.length > 0}
			<!-- Everything said under the comment that opened it, the agent's and the reader's alike -->
			<span class="cr-faint shrink-0 text-xs">{counted(thread.turns.length, { one: 'reply', many: 'replies' })}</span>
		{/if}
	</button>
	{#if unread}
		<NewReplyMark />
	{/if}
	{#if thread.resolved}
		<ReopenButton {thread} />
	{/if}
	<FoldToggle
		folded
		subject="this thread"
		testId="fold-comment"
		class="cr-thread-action cr-thread-action-icon cr-pressable"
		onToggle={unfold}
	/>
</div>
