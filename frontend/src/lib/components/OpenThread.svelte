<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorWrittenAgainst } from '$lib/anchors/views';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { useReview } from '$lib/review/context';
	import { messageOf } from '$lib/utils/errors';
	import { AGENT, raisedByAgent } from '$lib/utils/speakers';
	import CommentBox from './CommentBox.svelte';
	import ThreadConversation from './ThreadConversation.svelte';
	import ThreadHeading from './ThreadHeading.svelte';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();
	const writing = review.threads.writing;

	let failed = $state<string | null>(null);

	// The reply being written here, held by the review so that folding the
	// thread or its file, or reloading the page, keeps it
	const replying = $derived(writing.reply(thread.id));
	const awaiting = $derived(review.threads.reading.awaiting(thread.id));
	// Who spoke last: after an answer there is nothing new to hand over until
	// the reader says something. On a thread the agent raised, the opening
	// is already the agent's word.
	const lastWord = $derived(thread.turns.at(-1)?.author ?? thread.raised_by);
	const askable = $derived(review.canAsk && awaiting.length === 0 && lastWord !== AGENT);
	const raised = $derived(raisedByAgent(thread));
	// What has gone out with a round reads as read by the other side; what is
	// still unsent keeps the mark colour
	const sent = $derived(review.threads.sentInRound(thread.id) !== undefined);
	// What it was written against, kept for when the place it hangs on is gone
	const writtenAgainst = $derived(anchorWrittenAgainst(thread.anchor));

	/** Looking at the thread — clicking in it, or moving the keyboard into it — is what makes its answer read. */
	function markRead() {
		review.threads.reading.markRead(thread.id);
	}

	/** Add the reply being written; the keyboard stays with the thread, where the field was. */
	function reply(written: CommentField) {
		review.threads.say(written);
		review.sections.keyboardToThread(thread.id);
	}

	/** Add the reply being written, and hand the thread over with it. */
	function replyAndAsk(written: CommentField) {
		const said = review.threads.sayAndAsk(written);
		review.sections.keyboardToThread(said.thread);
		void asking(said.asked);
	}

	/** Put the reply being written away; the keyboard stays with the thread. */
	function putAway(written: CommentField) {
		writing.discard(written);
		review.sections.keyboardToThread(thread.id);
	}

	/** Wait for a question to be handed over, and say so if it could not be. */
	async function asking(handedOver: Promise<void>) {
		failed = null;
		try {
			await handedOver;
		} catch (error) {
			failed = messageOf(error);
		}
	}
</script>

<div
	class={[
		'cr-comment group rounded-r px-4 py-3',
		thread.anchor.outdated && 'cr-stale',
		sent && !raised && 'cr-sent',
		raised && 'cr-raised'
	]}
	role="presentation"
	onclick={markRead}
	onfocusin={markRead}
>
	<ThreadHeading {thread} />

	{#if thread.anchor.outdated && writtenAgainst.length > 0}
		<!-- One that has lost its place keeps its own copy of what was there -->
		<div data-testid="stale-quote" class="cr-stale-quote mb-3 rounded-r px-3 py-2">
			<p class="cr-muted mb-1 text-xs">what it was written against</p>
			{#each writtenAgainst as line, index (index)}
				<pre class="cr-code cr-muted overflow-x-auto font-mono">{line}</pre>
			{/each}
		</div>
	{/if}

	<ThreadConversation {thread} />

	{#if askable}
		<!-- Hands over everything said so far, the comment included, and hangs
			under the last of it rather than beside the empty field below. -->
		<div class="mt-3">
			<button
				type="button"
				data-testid="ask-now-thread"
				class="btn btn-outline btn-xs"
				onclick={() => asking(review.threads.ask(thread.id))}
			>
				{thread.turns.length === 0 ? 'Ask about this' : 'Ask about all this'}
			</button>
		</div>
	{/if}

	{#if failed}
		<p data-testid="ask-error" class="mt-2 text-xs text-error">{failed}</p>
	{/if}

	{#if replying}
		<div class="mt-3">
			<CommentBox
				field={replying}
				onSave={() => reply(replying)}
				onAsk={review.canAsk ? () => replyAndAsk(replying) : undefined}
				onCancel={() => putAway(replying)}
				severityPicker={false}
				nested
			/>
		</div>
	{:else}
		<div class="mt-3 border-t border-base-300 pt-3">
			<button
				type="button"
				data-testid="open-reply"
				class="cr-field cr-comment-body block w-full rounded px-3 py-1.5 text-left"
				onclick={() => writing.openReply(thread.id)}
			>
				<span class="cr-muted">Write a reply…</span>
			</button>
		</div>
	{/if}
</div>
