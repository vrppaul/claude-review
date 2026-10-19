<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorLabel } from '$lib/anchors/views';
	import { FOLD_TOGGLE_ROLE } from '$lib/dom/file-sections';
	import { useReview } from '$lib/review/context';
	import EdgeFrame from '$lib/ui/EdgeFrame.svelte';
	import type { FrameTone } from '$lib/ui/frame';
	import Icon from '$lib/ui/Icon.svelte';
	import Row from '$lib/ui/Row.svelte';
	import { raisedByAgent } from '$lib/utils/speakers';
	import { plainWords } from '$lib/utils/plain-words';
	import { counted, type CountedWords } from '$lib/utils/words';
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

{#snippet settled()}
	<Icon name="check" size="xs" tone="done" />
{/snippet}
{#snippet hangsOn()}
	<span class="cr-comment-ref">{anchorLabel(thread.anchor)}</span>
{/snippet}
{#snippet firstWords()}
	{plainWords(thread.body) || 'an image'}
{/snippet}
<!-- How many replies are under it, and whether one of them is new -->
{#snippet replies()}
	{#if thread.turns.length > 0}
		<span class="cr-faint">{counted(thread.turns.length, REPLIES)}</span>
	{/if}
	{#if unread}
		<NewReplyMark />
	{/if}
{/snippet}

<!-- Folded, by hand or by settling it: one row across the card it folds, the line it hangs on and the first words
	of what was said, one press anywhere on it to open it again, its chevron at the row's end. A settled one is taken
	up again by Reopen after the row, which gives up its width to it -->
<EdgeFrame tone={drawnAs.tone} ground="tint" testId={drawnAs.testId}>
	<div class={['flex items-center gap-3', folded === 'raised' && 'cr-raised']}>
		<div data-testid="folded-row" class="min-w-0 flex-1">
			<Row
				names="path"
				folded
				testId="unfold-thread"
				data-role={FOLD_TOGGLE_ROLE}
				leading={thread.resolved ? settled : undefined}
				label={hangsOn}
				said={firstWords}
				trailing={replies}
				onclick={unfold}
			/>
		</div>
		{#if thread.resolved}
			<ReopenButton {thread} />
		{/if}
	</div>
</EdgeFrame>
