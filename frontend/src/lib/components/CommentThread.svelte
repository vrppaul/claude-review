<script lang="ts">
	import type { Comment, CommentSeverity, Turn } from '$lib/types';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { reviewStore } from '$lib/stores/review.svelte';
	import { lineRangeLabel } from '$lib/utils/line-label';
	import { splitSuggestions } from '$lib/utils/suggestion';
	import CommentBox from './CommentBox.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';

	interface Props {
		comment: Comment;
	}

	let { comment }: Props = $props();
	let editing = $state(false);
	let replying = $state(false);
	let failed = $state<string | null>(null);
	let now = $state(Date.now());

	const label = $derived(lineRangeLabel(comment.side, comment.start_line, comment.end_line));
	// Which round it went out in, if it has. What is still unsent keeps the
	// mark colour; what has gone reads as already read by the other side.
	const sentIn = $derived(commentStore.sentInRound(comment.id));
	// In a diff, the same line number exists on both sides, so the thread says
	// which one it hangs on in the diff's own signs
	const sign = $derived(
		diffStore.mode !== 'diff' ? '' : comment.side === 'old' ? '−' : '+'
	);

	/** When a turn was said, to the minute — a thread is read, not audited. */
	function said(at: number | undefined): string {
		if (at === undefined) return '';
		return new Date(at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
	}

	interface Exchange {
		id: string;
		asked: string;
		round: number;
		at: number | undefined;
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
			answers: []
		};
		const list: Exchange[] = [opening];

		for (const turn of comment.turns) {
			if (turn.author === 'reader') {
				list.push({
					id: turn.id ?? `${comment.id}-${list.length}`,
					asked: turn.body,
					round: turn.round,
					at: turn.at,
					answers: []
				});
			} else {
				const belongsTo =
					list.find((exchange) => exchange.id === turn.answers) ?? list[list.length - 1];
				belongsTo.answers.push(turn);
			}
		}
		return list;
	});

	// Who spoke last: after an answer there is nothing new to hand over until
	// the reader says something
	const lastWord = $derived(comment.turns.at(-1)?.author ?? 'reader');

	function waitingFor(exchange: Exchange): number | null {
		const asked = comment.awaiting.find((w) => w.id === exchange.id);
		return asked ? Math.round((now - asked.at) / 1000) : null;
	}

	// How long each question has been with the author, so silence reads as
	// silence rather than as something broken
	$effect(() => {
		if (comment.awaiting.length === 0) return;
		const timer = setInterval(() => (now = Date.now()), 1000);
		return () => clearInterval(timer);
	});

	function handleSave(body: string, severity: CommentSeverity) {
		commentStore.update(comment.id, body, severity);
		editing = false;
	}

	/** Settling a thread folds it away; it can still be opened and read. */
	function resolve() {
		commentStore.setResolved(comment.id, true);
		commentStore.setCollapsed(comment.id, true);
	}

	function reply(body: string) {
		commentStore.addTurn(comment.id, 'reader', body);
		replying = false;
	}

	async function replyAndAsk(body: string) {
		commentStore.addTurn(comment.id, 'reader', body);
		replying = false;
		await handOver();
	}

	async function handOver() {
		failed = null;
		try {
			await commentStore.ask(comment.id);
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not ask';
		}
	}
</script>

<div id={comment.id} class="px-3 py-2">
	{#if editing}
		<CommentBox
			onSave={handleSave}
			onCancel={() => (editing = false)}
			initialBody={comment.body}
			initialSeverity={comment.severity}
			side={comment.side}
			startLine={comment.start_line}
			endLine={comment.end_line}
		/>
	{:else if comment.collapsed}
		<!-- Folded, by hand or by settling it. Either way it opens to be read. -->
		<div
			data-testid={comment.resolved ? 'resolved-thread' : 'folded-thread'}
			class="{comment.resolved ? 'cr-resolved' : 'cr-folded'} flex max-w-[96ch] items-center gap-3
			rounded-r px-4 py-2"
		>
			{#if comment.resolved}
				<svg
					class="h-3 w-3 shrink-0"
					viewBox="0 0 12 12"
					fill="currentColor"
					style="color: var(--cr-add-edge)"
					aria-hidden="true"><path d="M4.6 8.8L2 6.2l.9-.9 1.7 1.7L9.1 2.4l.9.9z" /></svg>
			{/if}
<button
				data-testid="fold-comment"
				class="btn btn-ghost btn-xs px-1"
				aria-expanded={!comment.collapsed}
				aria-label={comment.collapsed ? 'Unfold this thread' : 'Fold this thread away'}
				onclick={() => commentStore.setCollapsed(comment.id, !comment.collapsed)}
			>
				<svg
					class="h-3 w-3 transition-transform {comment.collapsed ? '-rotate-90' : ''}"
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
				onclick={() => commentStore.setCollapsed(comment.id, false)}
			>
				<span class="cr-comment-ref shrink-0 font-mono text-xs">{label}</span>
				<span class="cr-muted truncate text-sm">{comment.body}</span>
				{#if comment.turns.length > 0}
					<span class="cr-faint shrink-0 text-xs">
						{comment.turns.length}
						{comment.turns.length === 1 ? 'turn' : 'turns'}
					</span>
				{/if}
			</button>
			{#if comment.unread}
				<span class="shrink-0 text-xs" style="color: var(--cr-mark)">● new reply</span>
			{/if}
			{#if comment.resolved}
				<button
					data-testid="reopen-thread"
					class="btn btn-ghost btn-xs"
					onclick={() => commentStore.setResolved(comment.id, false)}
				>
					Reopen
				</button>
			{/if}
		</div>
	{:else}
		<!-- Looking at the thread is what makes its answer read -->
		<div
			class="cr-comment group rounded-r px-4 py-3 {comment.outdated ? 'cr-stale' : ''} {sentIn !==
			undefined
				? 'cr-sent'
				: ''}"
			role="presentation"
			onclick={() => commentStore.markRead(comment.id)}
		>
			<div class="mb-2 flex items-center gap-2">
				<button
				data-testid="fold-comment"
				class="btn btn-ghost btn-xs px-1"
				aria-expanded={!comment.collapsed}
				aria-label={comment.collapsed ? 'Unfold this thread' : 'Fold this thread away'}
				onclick={() => commentStore.setCollapsed(comment.id, !comment.collapsed)}
			>
				<svg
					class="h-3 w-3 transition-transform {comment.collapsed ? '-rotate-90' : ''}"
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
						class="font-mono text-xs {comment.side === 'old' ? 'cr-sign-del' : 'cr-sign-add'}"
						title={comment.side === 'old' ? 'on the line this change removed' : 'on the new line'}
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
				{#if comment.outdated}
					<span data-testid="comment-outdated" class="cr-severity cr-muted">outdated</span>
				{/if}
				{#if comment.resolved}
					<span data-testid="comment-resolved" class="cr-severity cr-muted">resolved</span>
				{/if}
				{#if comment.unread}
					<span
						data-testid="comment-unread"
						class="text-xs"
						style="color: var(--cr-mark)"
					>
						● new reply
					</span>
				{/if}
				<div class="flex-1"></div>
				{#if sentIn !== undefined}
					<span data-testid="comment-sent" class="cr-faint text-xs">sent · round {sentIn}</span>
				{/if}
				<div
					class="flex gap-1 opacity-45 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
				>
					<button
						data-testid="edit-comment"
						class="btn btn-ghost btn-xs"
						onclick={() => (editing = true)}
					>
						Edit
					</button>
					{#if comment.resolved}
						<button
							data-testid="reopen-comment"
							class="btn btn-ghost btn-xs"
							onclick={() => commentStore.setResolved(comment.id, false)}
						>
							Reopen
						</button>
					{:else}
						<button
							data-testid="resolve-comment"
							class="btn btn-ghost btn-xs"
							onclick={() => resolve()}
						>
							Resolve
						</button>
					{/if}
					<button
						data-testid="delete-comment"
						class="btn btn-ghost btn-xs hover:text-error"
						onclick={() => commentStore.remove(comment.id)}
					>
						Delete
					</button>
				</div>
			</div>

			{#if comment.outdated && comment.quote.length > 0}
				<div data-testid="stale-quote" class="cr-stale-quote mb-3 rounded-r px-3 py-2">
					<p class="cr-muted mb-1 text-xs">what it was written against</p>
					{#each comment.quote as line, i (i)}
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
							{#if comment.turns.length > 0}
								<p class="cr-who"><strong>You</strong> {said(exchange.at)}</p>
							{/if}
							{#each splitSuggestions(exchange.asked) as part, i (i)}
								{#if part.kind === 'suggestion'}
									<div data-testid="comment-suggestion" class="cr-suggestion mt-2 overflow-x-auto">
										{#each comment.quote as line, q (q)}
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
						</div>

						{#each exchange.answers as answer, i (i)}
							<div class="cr-reply">
								{#if i === 0}
									<span class="cr-tie" aria-hidden="true"></span>
								{/if}
								<div
									data-testid="thread-answer"
									class="cr-answer {comment.unread && i === exchange.answers.length - 1
										? 'cr-answer-new'
										: ''}"
								>
									<p class="cr-who"><strong>Author</strong> {said(answer.at)}</p>
									<MarkdownRenderer text={answer.body} dense />
								</div>
							</div>
						{/each}

						{#if waitingFor(exchange) !== null}
							<div class="cr-reply">
								{#if exchange.answers.length === 0}
									<span class="cr-tie" aria-hidden="true"></span>
								{/if}
								<div data-testid="awaiting-answer" class="cr-answer flex items-center gap-3">
									<span class="cr-who"><strong>Author</strong></span>
									<span class="flex items-center gap-1">
										<span class="cr-dot"></span><span class="cr-dot"></span><span class="cr-dot"
										></span>
									</span>
									<div class="flex-1"></div>
									<span class="cr-muted text-xs">
										asked {waitingFor(exchange)}s ago — keep reading, the answer lands here
									</span>
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>

			{#if reviewStore.canSendRound && comment.awaiting.length === 0 && lastWord !== 'author'}
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
						onSave={(body) => reply(body)}
						onAsk={reviewStore.canSendRound ? (body) => replyAndAsk(body) : undefined}
						onCancel={() => (replying = false)}
						severityPicker={false}
						nested
					/>
				</div>
			{:else}
				<div class="mt-3 border-t border-base-300 pt-3">
					<button
						data-testid="open-reply"
						class="cr-field cr-comment-body block w-full rounded px-3 py-1.5 text-left text-sm"
						onclick={() => (replying = true)}
					>
						<span class="cr-muted">Write a reply…</span>
					</button>
				</div>
			{/if}
		</div>
	{/if}
</div>
