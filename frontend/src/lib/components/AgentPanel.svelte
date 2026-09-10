<script lang="ts">
	import type { Comment } from '$lib/types';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { panelStore } from '$lib/stores/panel.svelte';
	import { reviewStore } from '$lib/stores/review.svelte';
	import { lineRangeLabel } from '$lib/utils/line-label';
	import { scrollToComment, showFile } from '$lib/utils/scroll';
	import { dragEdge, stepEdge } from '$lib/utils/resize';
	import { threadsIn, threadToken } from '$lib/utils/thread-token';
	import { formatWeight } from '$lib/utils/weight';
	import MarkdownRenderer from './MarkdownRenderer.svelte';

	let draft = $state('');
	let sending = $state(false);
	let failed = $state<string | null>(null);
	let now = $state(Date.now());
	let composer = $state<HTMLTextAreaElement | null>(null);
	let stream = $state<HTMLElement | null>(null);
	// Whether the reader is at the foot of the conversation. A turn landing
	// while they are reading an older one must not pull the panel out from
	// under them, so only the foot follows.
	let atFoot = $state(true);

	// The thread picker, opened by typing @ and closed by taking one or by
	// typing past it. `query` is what has been typed since the @.
	let picking = $state(false);
	let query = $state('');
	let highlighted = $state(0);

	const attached = $derived(reviewStore.canSendRound);
	const working = $derived(panelStore.working);
	// Threads this message points at, read back from the text every time: a
	// token deleted like a word takes its reference with it
	const pointed = $derived(threadsIn(draft, commentStore.comments));

	// Threads first — most questions are about something already commented on
	// — and then the files themselves, so a file nobody has marked can be
	// pointed at too. The agent can name any file; the reader should be able
	// to as well.
	const candidates = $derived([
		...commentStore.comments
			.filter((comment) => matches(`${comment.file} ${comment.body}`))
			.map((comment) => ({ kind: 'thread' as const, comment, path: comment.file })),
		...diffStore.files
			.filter((file) => matches(file.path))
			.map((file) => ({ kind: 'file' as const, comment: undefined, path: file.path }))
	]);

	function matches(against: string): boolean {
		return against.toLowerCase().includes(query.toLowerCase());
	}

	// When the agent last said anything, so silence can be read as silence
	const lastAnswer = $derived(
		[...panelStore.turns].reverse().find((turn) => turn.author === 'author')?.at
	);

	/** How long ago, in the words a conversation uses. */
	function since(at: number | null | undefined): string {
		if (at === undefined || at === null) return '';
		const seconds = Math.max(0, Math.round((now - at) / 1000));
		if (seconds < 60) return `${seconds}s ago`;
		if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
		return `${Math.round(seconds / 3600)}h ago`;
	}

	function said(at: number): string {
		return new Date(at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
	}

	function label(comment: Comment): string {
		const file = comment.file.split('/').pop() ?? comment.file;
		return `${file} ${lineRangeLabel(comment.side, comment.start_line, comment.end_line)}`;
	}

	/** What a thread is in, so the picker says whether it is still live. */
	function threadState(comment: Comment): string {
		if (comment.outdated) return 'outdated';
		if (comment.resolved) return 'resolved';
		if (comment.turns.length > 0) {
			return `${comment.turns.length} ${comment.turns.length === 1 ? 'turn' : 'turns'}`;
		}
		return '';
	}

	/** Near enough to the bottom that the conversation should keep following. */
	function onScroll() {
		if (!stream) return;
		atFoot = stream.scrollHeight - stream.scrollTop - stream.clientHeight < 80;
	}

	// A new turn is the point of the panel, so it is brought into view. The
	// count is what this watches: it changes exactly when something is said.
	$effect(() => {
		const said = panelStore.turns.length;
		if (said === 0 || !stream || !atFoot) return;
		const shown = stream;
		requestAnimationFrame(() => {
			// Asked again: the reader may have scrolled away in the frame it
			// took the turn to be laid out
			if (atFoot) shown.scrollTop = shown.scrollHeight;
		});
	});

	// A clock only while something is waiting on it
	$effect(() => {
		if (!working && !panelStore.agent.at && lastAnswer === undefined) return;
		const timer = setInterval(() => (now = Date.now()), 1000);
		return () => clearInterval(timer);
	});

	function openPicker() {
		picking = true;
		query = '';
		highlighted = 0;
		composer?.focus();
	}

	/** Watch what is being typed for an @ that has not been finished yet. */
	function onInput(event: Event & { currentTarget: HTMLTextAreaElement }) {
		const field = event.currentTarget;
		draft = field.value;
		const opening = /@([^\s@]*)$/.exec(field.value.slice(0, field.selectionStart));
		picking = opening !== null;
		query = opening?.[1] ?? '';
		highlighted = 0;
	}

	/** Put the token where the @ was, and carry on typing. */
	function take(pick: { comment?: Comment; path: string }) {
		const field = composer;
		if (!field) return;
		const caret = field.selectionStart;
		const before = draft.slice(0, caret).replace(/@[^\s@]*$/, '');
		const after = draft.slice(caret);
		const token = `${pick.comment ? threadToken(pick.comment) : `@${pick.path}`} `;
		draft = `${before}${token}${after}`;
		picking = false;
		field.focus();
		requestAnimationFrame(() => {
			const at = before.length + token.length;
			field.setSelectionRange(at, at);
		});
	}

	/** Take a thread out of the message by taking its token out of the words. */
	function drop(comment: Comment) {
		draft = draft.split(threadToken(comment)).join('').replace(/ {2,}/g, ' ');
	}

	function onKeydown(event: KeyboardEvent) {
		if (picking && candidates.length > 0) {
			if (event.key === 'ArrowDown') {
				event.preventDefault();
				highlighted = (highlighted + 1) % candidates.length;
				return;
			}
			if (event.key === 'ArrowUp') {
				event.preventDefault();
				highlighted = (highlighted - 1 + candidates.length) % candidates.length;
				return;
			}
			if (event.key === 'Enter' && !event.shiftKey) {
				event.preventDefault();
				take(candidates[highlighted]);
				return;
			}
		}
		if (event.key === 'Escape' && picking) {
			event.preventDefault();
			picking = false;
			return;
		}
		if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
			event.preventDefault();
			void send();
		}
	}

	async function send() {
		const text = draft.trim();
		if (!text || sending || !attached) return;
		sending = true;
		failed = null;
		// Sending is a deliberate act: it always brings you back to the foot
		atFoot = true;
		try {
			await panelStore.send(text, pointed);
			draft = '';
			picking = false;
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not send';
		} finally {
			sending = false;
		}
	}

	async function stop(messageId: string) {
		failed = null;
		try {
			await panelStore.cancel(messageId);
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not stop it';
		}
	}

	/** The panel is on the right, so dragging left is what widens it. */
	const sizing = $derived({
		width: panelStore.width,
		grows: 'left' as const,
		onWidth: (px: number) => panelStore.setWidth(px)
	});
</script>

<aside
	data-testid="agent-panel"
	class="cr-panel flex min-h-0 shrink-0 flex-col border-l border-base-300"
	style="width: {panelStore.width}px"
>
	<!-- The reader's own width, dragged or stepped with the arrow keys -->
	<button
		data-testid="panel-resize"
		class="cr-panel-grip"
		aria-label="Resize the panel"
		onpointerdown={(e) => dragEdge(e, sizing)}
		onkeydown={(e) => stepEdge(e, sizing)}
	></button>

	<header
		data-testid="panel-status"
		class="flex h-9 shrink-0 items-center gap-2 border-b border-base-300 bg-base-200 px-3"
	>
		<span
			class="h-1.5 w-1.5 shrink-0 rounded-full"
			style="background: {attached
				? working
					? 'var(--cr-mark)'
					: 'var(--cr-add-edge)'
				: 'var(--color-base-300)'}"
		></span>
		<span class="text-sm font-semibold {attached ? '' : 'cr-muted'}">
			{attached ? 'Agent' : 'No agent attached'}
		</span>
		{#if panelStore.agent.model}
			<span data-testid="agent-model" class="cr-faint font-mono text-xs">
				{panelStore.agent.model}
			</span>
		{/if}
		<div class="flex-1"></div>
		{#if working}
			<span class="cr-faint text-xs">{since(working.at)}</span>
		{:else if lastAnswer !== undefined}
			<span data-testid="agent-last-answer" class="cr-faint text-xs">
				answered {since(lastAnswer)}
			</span>
		{/if}
		<button
			data-testid="close-panel"
			class="btn btn-ghost btn-xs px-1"
			aria-label="Hide the agent panel"
			onclick={() => panelStore.setOpen(false)}
		>
			<svg class="h-3 w-3 -rotate-90" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
				<path d="M2 4l4 4 4-4z" />
			</svg>
		</button>
	</header>

	<!-- Two numbers, told apart: one this side measures, one the agent reports -->
	<div class="flex shrink-0 flex-wrap items-center gap-2 border-b border-base-300 px-3 py-1.5">
		<span data-testid="review-weight" class="cr-pill" title="What handing this review over costs">
			review {formatWeight(panelStore.weight)}
		</span>
		{#if panelStore.agent.context}
			<span data-testid="agent-context" class="cr-pill">
				context {panelStore.agent.context} · as reported {since(panelStore.agent.at)}
			</span>
		{/if}
	</div>

	<div
		data-testid="panel-turns"
		bind:this={stream}
		onscroll={onScroll}
		class="min-h-0 flex-1 overflow-y-auto px-3 py-3"
	>
		{#if panelStore.turns.length === 0}
			{#if attached}
				<div
					data-testid="panel-empty"
					class="flex h-full flex-col items-center justify-center gap-3 px-6 text-center"
				>
					<svg
						class="h-5 w-5"
						viewBox="0 0 16 16"
						fill="none"
						stroke="currentColor"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
						style="color: var(--color-base-300)"
						aria-hidden="true"
					>
						<path d="M2.5 4.5h11v7h-6l-3 2.5v-2.5h-2z"></path>
					</svg>
					<p class="cr-faint text-sm leading-relaxed">
						Ask about anything — the plan, the tests, a file nobody commented on. A thread is about
						one line; this is about the rest.
					</p>
				</div>
			{:else}
				<div
					data-testid="panel-unattached"
					class="flex h-full flex-col items-center justify-center gap-3 px-4 text-center"
				>
					<p class="cr-faint text-sm leading-relaxed">
						This review runs in the foreground, so nothing is waiting to answer. Start it in the
						background and keep the answering half in a loop:
					</p>
					<pre
						class="cr-code cr-muted w-full overflow-x-auto rounded border border-base-300 bg-base-200 px-3 py-2 text-left">claude-review --no-open diff &
claude-review wait --port &lt;port&gt;</pre>
				</div>
			{/if}
		{:else}
			<div class="flex flex-col gap-3">
				{#each panelStore.turns as turn (turn.id)}
					{#if turn.author === 'event'}
						{@const raised = commentStore.comments.find((c) => c.id === turn.threads?.[0])}
						<div data-testid="panel-event" class="cr-round-mark">
							<span></span>
							{#if raised}
								<button
									data-testid="panel-thread-ref"
									class="cr-thread-chip"
									onclick={() => scrollToComment(raised.id, raised.file)}
								>
									{turn.body}
								</button>
							{:else}
								<span class="cr-faint text-xs">{turn.body}</span>
							{/if}
							<span></span>
						</div>
					{:else if turn.author === 'reader'}
						<div
							data-testid="panel-said"
							class="cr-panel-said rounded-r px-3 py-2 {turn.cancelled ? 'opacity-60' : ''}"
						>
							<p class="cr-who"><strong>You</strong> {said(turn.at)}</p>
							<MarkdownRenderer text={turn.body} dense />
							{#if turn.threads && turn.threads.length > 0}
								<div class="mt-2 flex flex-wrap gap-1">
									{#each turn.threads as id (id)}
										{@const thread = commentStore.comments.find((c) => c.id === id)}
										{#if thread}
											<button
												data-testid="panel-thread-ref"
												class="cr-thread-chip"
												onclick={() => scrollToComment(thread.id, thread.file)}
											>
												{label(thread)}
											</button>
										{/if}
									{/each}
								</div>
							{/if}
							{#if turn.cancelled}
								<p data-testid="panel-cancelled" class="cr-faint mt-1 text-xs">
									stopped — the agent was asked to drop it
								</p>
							{/if}
						</div>
					{:else}
						<div data-testid="panel-answer" class="cr-answer">
							<p class="cr-who"><strong>Author</strong> {said(turn.at)}</p>
							<MarkdownRenderer text={turn.body} dense />
							{#if turn.files && turn.files.length > 0}
								<div class="mt-2 flex flex-wrap gap-1">
									{#each turn.files as path (path)}
										<button
											data-testid="answer-file"
											class="cr-thread-chip"
											onclick={() => showFile(path)}
										>
											{path.split('/').pop()}
										</button>
									{/each}
								</div>
							{/if}
						</div>
					{/if}
				{/each}

				{#if working}
					<div data-testid="panel-working" class="cr-answer flex flex-col gap-2">
						<div class="flex items-center gap-3">
							<span class="cr-who"><strong>Author</strong></span>
							<span class="flex items-center gap-1">
								<span class="cr-dot"></span><span class="cr-dot"></span><span class="cr-dot"></span>
							</span>
							<div class="flex-1"></div>
							<span class="cr-faint text-xs">working {since(working.at)}</span>
							<button
								data-testid="stop-message"
								class="btn btn-outline btn-xs"
								onclick={() => stop(working.id)}
							>
								Stop
							</button>
						</div>
						{#if panelStore.progress}
							<!-- What is being done, in its own words, replaced as it changes -->
							{#if panelStore.progress.text}
								<p data-testid="panel-progress" class="cr-progress text-sm">
									{panelStore.progress.text}
								</p>
							{/if}
							{#if panelStore.progress.steps.length > 0}
								<!-- Branches of the same work, drawn hanging off it -->
								<ul data-testid="progress-steps" class="cr-branches">
									{#each panelStore.progress.steps as step (step.text)}
										<li class="cr-branch {step.done ? 'cr-branch-done' : ''}">
											{#if step.done}
												<svg
													class="cr-branch-mark"
													viewBox="0 0 12 12"
													fill="currentColor"
													aria-hidden="true"><path d="M4.6 8.8L2 6.2l.9-.9 1.7 1.7L9.1 2.4l.9.9z" /></svg>
											{:else}
												<span class="cr-branch-mark"><span class="cr-dot"></span></span>
											{/if}
											<span>{step.text}</span>
										</li>
									{/each}
								</ul>
							{/if}
							{#if panelStore.progress.files.length > 0}
								<div class="flex flex-wrap gap-1">
									{#each panelStore.progress.files as path (path)}
										<button
											data-testid="progress-file"
											class="cr-thread-chip"
											onclick={() => showFile(path)}
										>
											{path.split('/').pop()}
										</button>
									{/each}
								</div>
							{/if}
						{/if}
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<div class="relative shrink-0 border-t border-base-300 px-3 py-2">
		{#if picking && candidates.length > 0}
			<div data-testid="thread-picker" class="cr-picker">
				{#each candidates as pick, index (pick.comment?.id ?? pick.path)}
					<button
						data-testid={pick.comment ? 'thread-option' : 'file-option'}
						class="cr-picker-row {index === highlighted ? 'cr-picker-on' : ''}"
						onclick={() => take(pick)}
					>
						<span class="cr-comment-ref block truncate font-mono text-xs">
							{pick.comment ? label(pick.comment) : pick.path}
						</span>
						{#if pick.comment}
							<span class="cr-muted block truncate text-sm">
								{pick.comment.body}{threadState(pick.comment)
									? ` · ${threadState(pick.comment)}`
									: ''}
							</span>
						{:else}
							<span class="cr-faint block truncate text-sm">file</span>
						{/if}
					</button>
				{/each}
			</div>
		{/if}

		{#if attached}
			{#if pointed.length > 0}
				<div class="mb-2 flex flex-wrap gap-1">
					{#each pointed as comment (comment.id)}
						<span data-testid="pointed-thread" class="cr-thread-chip">
							{label(comment)}
							<button
								data-testid="drop-thread"
								class="px-1"
								aria-label="Take this thread out of the message"
								onclick={() => drop(comment)}>×</button
							>
						</span>
					{/each}
				</div>
			{/if}
			<textarea
				data-testid="panel-input"
				bind:this={composer}
				class="cr-field cr-comment-body w-full resize-y rounded px-3 py-2"
				rows="2"
				placeholder="Ask about anything…"
				value={draft}
				oninput={onInput}
				onkeydown={onKeydown}
			></textarea>
			<div class="mt-2 flex items-center gap-2">
				<button data-testid="mention-thread" class="btn btn-ghost btn-xs" onclick={openPicker}>
					@ thread
				</button>
				<span class="cr-faint hidden text-xs lg:inline">Ctrl+Enter sends</span>
				<div class="flex-1"></div>
				{#if failed}
					<span data-testid="panel-error" class="text-xs text-error">{failed}</span>
				{/if}
				<button
					data-testid="send-message"
					class="btn btn-primary btn-xs"
					disabled={draft.trim().length === 0 || sending}
					onclick={send}
				>
					{sending ? 'Sending' : 'Send'}
				</button>
			</div>
		{:else}
			<p data-testid="panel-read-only" class="cr-faint py-1 text-center text-xs">
				The panel is read-only until someone is listening.
			</p>
		{/if}
	</div>
</aside>
