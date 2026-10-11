<script lang="ts">
	import type { Thread, Turn } from '$lib/types';
	import { anchorLabel } from '$lib/anchors/views';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { messageOf } from '$lib/utils/errors';
	import { splitSuggestions } from '$lib/utils/suggestion';
	import { clockTime, timeAgo } from '$lib/utils/time';
	import { useReview } from '$lib/review/context';
	import CommentBox from './CommentBox.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import SaidImages from './SaidImages.svelte';

	interface Props {
		comment: Thread;
	}

	// What the thread says when it could not be handed over and nothing said why
	const ASKING_FAILED = 'Could not ask';

	let { comment }: Props = $props();
	const review = useReview();
	let failed = $state<string | null>(null);
	let container: HTMLElement | undefined = $state();

	// Announced to the review, which brings the thread into view by it, never by an id on the page
	$effect(() => (container ? review.sections.registerThread(comment.id, container) : undefined));

	const reading = review.threads.reading;
	const writing = review.threads.writing;
	// What is being written here, held by the review so that folding the thread
	// or its file, or reloading the page, keeps it
	const editing = $derived(writing.edit(comment.id));
	const replying = $derived(writing.reply(comment.id));
	const label = $derived(anchorLabel(comment.anchor));
	const folded = $derived(reading.isFolded(comment.id));
	const unread = $derived(reading.isUnread(comment.id));
	// Questions in this thread still with the agent, oldest first
	const awaiting = $derived(reading.awaiting(comment.id));
	// Which round it went out in, if it has. What is still unsent keeps the
	// mark colour; what has gone reads as already read by the other side.
	const sentIn = $derived(review.threads.sentInRound(comment.id));
	// In a diff, the same line number exists on both sides, so the thread says
	// which one it hangs on in the diff's own signs
	const side = $derived(comment.anchor.kind === 'line' ? comment.anchor.side : null);
	const sign = $derived(review.mode !== 'diff' || side === null ? '' : side === 'old' ? '−' : '+');

	/** When a turn was said; a turn kept from an older version may not say. */
	function said(at: number | undefined): string {
		return at === undefined ? '' : clockTime(at);
	}

	interface Exchange {
		id: string;
		asked: string;
		round: number;
		at: number | undefined;
		images: string[];
		answers: Turn[];
	}

	/**
	 * The thread as questions and the answers to them.
	 *
	 * An answer says which question it belongs to, so two questions asked
	 * before either is answered still read straight: each answer lands under
	 * its own. An answer from an older version, which named nothing, falls to
	 * the last question — where it used to go anyway.
	 */
	const exchanges = $derived.by(() => {
		const opening: Exchange = {
			id: comment.id,
			asked: comment.body,
			round: comment.round,
			at: comment.at,
			images: comment.images,
			answers: []
		};
		const list: Exchange[] = [opening];

		for (const turn of comment.turns) {
			if (turn.author === 'reader') {
				list.push({
					id: turn.id,
					asked: turn.body,
					round: turn.round,
					at: turn.at,
					images: turn.images,
					answers: []
				});
			} else {
				const belongsTo = list.find((exchange) => exchange.id === turn.answers) ?? list[list.length - 1];
				belongsTo.answers.push(turn);
			}
		}
		return list;
	});

	// Who spoke last: after an answer there is nothing new to hand over until
	// the reader says something. On a thread the author raised, the opening
	// is already the author's word.
	const lastWord = $derived(comment.turns.at(-1)?.author ?? comment.raised_by);
	// A thread the author raised is not one of the reader's marks, and is
	// not drawn as if it were
	const raised = $derived(comment.raised_by === 'author');

	/**
	 * How long a question has been with the agent, if it is still waited on,
	 * so silence reads as silence rather than as something broken.
	 */
	function waitingFor(exchange: Exchange): string | null {
		const asked = awaiting.find((question) => question.id === exchange.id);
		return asked ? timeAgo(asked.at, review.clock.now) : null;
	}

	/** Settling a thread folds it away; it can still be opened and read. */
	function resolve() {
		review.threads.setResolved(comment.id, true);
	}

	/** Hand the thread over as it stands, and carry on reading. */
	function handOver() {
		void asking(review.threads.ask(comment.id));
	}

	/** Add the reply being written, and hand the thread over with it. */
	function replyAndAsk(written: CommentField) {
		void asking(review.threads.sayAndAsk(written));
	}

	/** Wait for a question to be handed over, and say so if it could not be. */
	async function asking(handedOver: Promise<void>) {
		failed = null;
		try {
			await handedOver;
		} catch (error) {
			failed = messageOf(error, ASKING_FAILED);
		}
	}
</script>

<div bind:this={container} data-testid="comment-thread" data-thread-id={comment.id} class="px-3 py-2">
	{#if editing}
		<CommentBox
			field={editing}
			onSave={() => review.threads.say(editing)}
			onCancel={() => writing.discard(editing)}
			{label}
		/>
	{:else if folded}
		<!-- Folded, by hand or by settling it. Either way it opens to be read. -->
		<div
			data-testid={comment.resolved ? 'resolved-thread' : 'folded-thread'}
			class="{comment.resolved
				? 'cr-resolved'
				: comment.raised_by === 'author'
					? 'cr-folded cr-raised'
					: 'cr-folded'} flex max-w-[96ch] items-center gap-3
			rounded-r px-4 py-2"
		>
			{#if comment.resolved}
				<svg
					class="h-3 w-3 shrink-0"
					viewBox="0 0 12 12"
					fill="currentColor"
					style="color: var(--cr-add-edge)"
					aria-hidden="true"><path d="M4.6 8.8L2 6.2l.9-.9 1.7 1.7L9.1 2.4l.9.9z" /></svg
				>
			{/if}
			<button
				data-testid="fold-comment"
				class="btn btn-ghost btn-xs px-1"
				aria-expanded={!folded}
				aria-label={folded ? 'Unfold this thread' : 'Fold this thread away'}
				onclick={() => reading.setFolded(comment.id, !folded)}
			>
				<svg
					class="h-3 w-3 transition-transform {folded ? '-rotate-90' : ''}"
					viewBox="0 0 12 12"
					fill="currentColor"
					aria-hidden="true"
				>
					<path d="M2 4l4 4 4-4z" />
				</svg>
			</button>
			<button
				data-testid="unfold-thread"
				class="flex min-w-0 flex-1 items-baseline gap-3 text-left"
				onclick={() => reading.setFolded(comment.id, false)}
			>
				<span class="cr-comment-ref shrink-0 font-mono text-xs">{label}</span>
				<span class="cr-muted truncate text-sm">{comment.body || 'an image'}</span>
				{#if comment.turns.length > 0}
					<span class="cr-faint shrink-0 text-xs">
						{comment.turns.length}
						{comment.turns.length === 1 ? 'turn' : 'turns'}
					</span>
				{/if}
			</button>
			{#if unread}
				<span class="shrink-0 text-xs" style="color: var(--cr-mark)">● new reply</span>
			{/if}
			{#if comment.resolved}
				<button
					data-testid="reopen-thread"
					class="btn btn-ghost btn-xs"
					onclick={() => review.threads.setResolved(comment.id, false)}
				>
					Reopen
				</button>
			{/if}
		</div>
	{:else}
		<!-- Looking at the thread is what makes its answer read -->
		<div
			class="cr-comment group rounded-r px-4 py-3 {comment.anchor.outdated ? 'cr-stale' : ''} {sentIn !== undefined &&
			!raised
				? 'cr-sent'
				: ''} {raised ? 'cr-raised' : ''}"
			role="presentation"
			onclick={() => reading.markRead(comment.id)}
		>
			<div class="mb-2 flex items-center gap-2">
				<button
					data-testid="fold-comment"
					class="btn btn-ghost btn-xs px-1"
					aria-expanded={!folded}
					aria-label={folded ? 'Unfold this thread' : 'Fold this thread away'}
					onclick={() => reading.setFolded(comment.id, !folded)}
				>
					<svg
						class="h-3 w-3 transition-transform {folded ? '-rotate-90' : ''}"
						viewBox="0 0 12 12"
						fill="currentColor"
						aria-hidden="true"
					>
						<path d="M2 4l4 4 4-4z" />
					</svg>
				</button>
				{#if sign}
					<span
						data-testid="comment-side"
						class="font-mono text-xs {side === 'old' ? 'cr-sign-del' : 'cr-sign-add'}"
						title={side === 'old' ? 'on the line this change removed' : 'on the new line'}
					>
						{sign}
					</span>
				{/if}
				<span data-testid="comment-line-label" class="cr-comment-ref font-mono text-xs">
					{label}
				</span>
				{#if comment.severity !== 'note'}
					<span data-testid="comment-severity" class="cr-severity cr-severity-{comment.severity}"
						>{comment.severity}</span
					>
				{/if}
				{#if comment.anchor.outdated}
					<span data-testid="comment-outdated" class="cr-severity cr-muted">outdated</span>
				{/if}
				{#if comment.resolved}
					<span data-testid="comment-resolved" class="cr-severity cr-muted">resolved</span>
				{/if}
				{#if unread}
					<span data-testid="comment-unread" class="text-xs" style="color: var(--cr-mark)"> ● new reply </span>
				{/if}
				<div class="flex-1"></div>
				{#if raised}
					<span data-testid="comment-raised" class="cr-severity cr-raised-tag">from the agent</span>
				{:else if sentIn !== undefined}
					<span data-testid="comment-sent" class="cr-faint text-xs">sent · round {sentIn}</span>
				{/if}
				<div class="flex gap-1 opacity-45 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
					<button data-testid="edit-comment" class="btn btn-ghost btn-xs" onclick={() => writing.openEdit(comment)}>
						Edit
					</button>
					{#if comment.resolved}
						<button
							data-testid="reopen-comment"
							class="btn btn-ghost btn-xs"
							onclick={() => review.threads.setResolved(comment.id, false)}
						>
							Reopen
						</button>
					{:else}
						<button data-testid="resolve-comment" class="btn btn-ghost btn-xs" onclick={() => resolve()}>
							Resolve
						</button>
					{/if}
					<button
						data-testid="delete-comment"
						class="btn btn-ghost btn-xs hover:text-error"
						onclick={() => review.threads.remove(comment.id)}
					>
						Delete
					</button>
				</div>
			</div>

			{#if comment.anchor.outdated && comment.anchor.quote.length > 0}
				<div data-testid="stale-quote" class="cr-stale-quote mb-3 rounded-r px-3 py-2">
					<p class="cr-muted mb-1 text-xs">what it was written against</p>
					{#each comment.anchor.quote as line, i (i)}
						<pre class="cr-code cr-muted overflow-x-auto font-mono">{line}</pre>
					{/each}
				</div>
			{/if}

			<div class="cr-thread">
				{#each exchanges as exchange, index (index)}
					{#if index > 0 && exchange.round !== exchanges[index - 1].round}
						<!-- Where one round ended and the next began, in this thread -->
						<div data-testid="round-mark" class="cr-round-mark">
							<span></span>
							<span class="cr-faint text-xs">round {exchange.round}</span>
							<span></span>
						</div>
					{/if}
					<div class="cr-exchange">
						<div>
							{#if index === 0 && raised}
								<p class="cr-who"><strong>Agent</strong> {said(exchange.at)}</p>
							{:else if comment.turns.length > 0}
								<p class="cr-who"><strong>You</strong> {said(exchange.at)}</p>
							{/if}
							{#each splitSuggestions(exchange.asked) as part, i (i)}
								{#if part.kind === 'suggestion'}
									<div data-testid="comment-suggestion" class="cr-suggestion mt-2 overflow-x-auto">
										{#each comment.anchor.quote as line, q (q)}
											<div class="cr-sugg-row cr-sugg-del"><span class="cr-sugg-sign">−</span>{line}</div>
										{/each}
										{#each part.text.split('\n') as line, a (a)}
											<div class="cr-sugg-row cr-sugg-add"><span class="cr-sugg-sign">+</span>{line}</div>
										{/each}
									</div>
								{:else}
									<MarkdownRenderer text={part.text} dense />
								{/if}
							{/each}
							<SaidImages images={exchange.images} />
						</div>

						{#each exchange.answers as answer, i (i)}
							<div class="cr-reply">
								{#if i === 0}
									<span class="cr-tie" aria-hidden="true"></span>
								{/if}
								<div
									data-testid="thread-answer"
									data-tour="answer"
									class="cr-answer {unread && i === exchange.answers.length - 1 ? 'cr-answer-new' : ''}"
								>
									<p class="cr-who"><strong>Agent</strong> {said(answer.at)}</p>
									<MarkdownRenderer text={answer.body} dense />
								</div>
							</div>
						{/each}

						{#if waitingFor(exchange) !== null}
							<div class="cr-reply">
								{#if exchange.answers.length === 0}
									<span class="cr-tie" aria-hidden="true"></span>
								{/if}
								<div data-testid="awaiting-answer" data-tour="awaited-answer" class="cr-answer flex items-center gap-3">
									<span class="cr-who"><strong>Agent</strong></span>
									<span class="flex items-center gap-1">
										<span class="cr-dot"></span><span class="cr-dot"></span><span class="cr-dot"></span>
									</span>
									<div class="flex-1"></div>
									<span class="cr-muted text-xs">
										asked {waitingFor(exchange)} — keep reading, the answer lands here
									</span>
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>

			{#if review.answerer.attached && awaiting.length === 0 && lastWord !== 'author'}
				<!-- Hands over everything said so far, the comment included, and hangs
					under the last of it rather than beside the empty field below. -->
				<div class="mt-3">
					<button data-testid="ask-now-thread" class="btn btn-outline btn-xs" onclick={handOver}>
						{comment.turns.length === 0 ? 'Ask about this' : 'Ask about all this'}
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
						onSave={() => review.threads.say(replying)}
						onAsk={review.answerer.attached ? () => replyAndAsk(replying) : undefined}
						onCancel={() => writing.discard(replying)}
						severityPicker={false}
						nested
					/>
				</div>
			{:else}
				<div class="mt-3 border-t border-base-300 pt-3">
					<button
						data-testid="open-reply"
						class="cr-field cr-comment-body block w-full rounded px-3 py-1.5 text-left text-sm"
						onclick={() => writing.openReply(comment.id)}
					>
						<span class="cr-muted">Write a reply…</span>
					</button>
				</div>
			{/if}
		</div>
	{/if}
</div>
