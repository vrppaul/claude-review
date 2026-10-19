<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorLabel } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import EdgeFrame from '$lib/ui/EdgeFrame.svelte';
	import type { FrameTone } from '$lib/ui/frame';
	import Icon from '$lib/ui/Icon.svelte';
	import { raisedByAgent } from '$lib/utils/speakers';
	import { plainWords } from '$lib/utils/plain-words';
	import { counted, type CountedWords } from '$lib/utils/words';
	import FoldToggle from './FoldToggle.svelte';
	import NewReplyMark from './NewReplyMark.svelte';
	import ReopenButton from './ReopenButton.svelte';

	interface Props {
		thread: Thread;
	}

	/** Why a thread is folded to a line: settled, or put away by hand, the agent's or the reader's. */
	type Folded = 'settled' | 'raised' | 'theirs';

	// How each is drawn: settled, stepping back; put away, in the colour of whose thread it is
	const DRAWN_AS: Record<Folded, { tone: FrameTone; testId: string }> = {
		settled: { tone: 'quiet', testId: 'resolved-thread' },
		raised: { tone: 'agent', testId: 'folded-thread' },
		theirs: { tone: 'reader', testId: 'folded-thread' }
	};
	// What everything said under the comment that opened a thread is called, counted: the agent's and the reader's alike
	const REPLIES: CountedWords = { one: 'reply', many: 'replies' };

	let { thread }: Props = $props();
	const review = useReview();

	const unread = $derived(review.threads.reading.isUnread(thread.id));
	const folded = $derived.by<Folded>(() => {
		if (thread.resolved) return 'settled';
		return raisedByAgent(thread) ? 'raised' : 'theirs';
	});
	const drawnAs = $derived(DRAWN_AS[folded]);

	/** Open the thread again; the keyboard stays on its toggle, drawn anew at the head of the open thread. */
	function unfold() {
		review.threads.reading.setFolded(thread.id, false);
		review.sections.keyboardToThreadFold(thread.id);
	}
</script>

<!-- Folded, by hand or by settling it: one line as wide as the card it folds, and the first words of what
	was said. Either way it opens to be read, by the chevron where the open card has it, at the far end -->
<EdgeFrame tone={drawnAs.tone} ground="tint" testId={drawnAs.testId}>
	<div class={['flex items-center gap-3', folded === 'raised' && 'cr-raised']}>
		{#if thread.resolved}
			<span class="text-(--cr-done)"><Icon name="check" size="xs" /></span>
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
				<span class="cr-faint shrink-0 text-xs">{counted(thread.turns.length, REPLIES)}</span>
			{/if}
		</button>
		{#if unread}
			<NewReplyMark />
		{/if}
		{#if thread.resolved}
			<ReopenButton {thread} />
		{/if}
		<FoldToggle folded subject="this thread" testId="fold-comment" tone="secondary" onToggle={unfold} />
	</div>
</EdgeFrame>
