<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorShortPlace, anchorToken } from '$lib/anchors/views';
	import { threadsIn } from '$lib/anchors/thread-token';
	import { formatWeight } from '$lib/review/weight';
	import { useReview } from '$lib/review/context';
	import { messageOf } from '$lib/utils/errors';
	import { clockTime, timeAgo } from '$lib/utils/time';
	import AttachedImages from './AttachedImages.svelte';
	import EdgeGrip from './EdgeGrip.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import SaidImages from './SaidImages.svelte';
	import Icon from './Icon.svelte';
	import TypingIndicator from './TypingIndicator.svelte';

	// What the panel says when a message could not be sent or taken back, and nothing said why
	const SENDING_FAILED = 'Could not send';
	const STOPPING_FAILED = 'Could not stop it';

	const review = useReview();

	let sending = $state(false);
	let failed = $state<string | null>(null);
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

	const attached = $derived(review.answerer.attached);
	const working = $derived(review.conversation.working);
	// The message being written lives in the review's composer, so hiding
	// the panel or reloading the page does not lose it
	const draft = $derived(review.conversation.composer.text);
	// Threads this message points at, read back from the text every time: a
	// token deleted like a word takes its reference with it
	const pointed = $derived(threadsIn(draft, review.threads.all));
	// A screenshot can be the whole question, so words are not required
	const sayable = $derived(draft.trim().length > 0 || review.conversation.composer.attachments.images.length > 0);

	// Threads first — most questions are about something already commented on
	// — and then the files themselves, so a file nobody has marked can be
	// pointed at too. The agent can name any file; the reader should be able
	// to as well.
	type Candidate = { kind: 'thread'; comment: Thread } | { kind: 'file'; path: string };
	const candidates = $derived<Candidate[]>([
		...review.threads.all
			.filter((comment) => matches(`${anchorToken(comment.anchor)} ${comment.body}`))
			.map((comment) => ({ kind: 'thread' as const, comment })),
		...review.diff.files
			.filter((file) => matches(file.path))
			.map((file) => ({ kind: 'file' as const, path: file.path }))
	]);

	function matches(against: string): boolean {
		return against.toLowerCase().includes(query.toLowerCase());
	}

	// When the agent last said anything, so silence can be read as silence
	const lastAnswer = $derived([...review.conversation.turns].reverse().find((turn) => turn.author === 'author')?.at);

	/** How long ago, read off the review's clock, so it moves on while it is on screen. */
	function since(at: number): string {
		return timeAgo(at, review.clock.now);
	}

	/** How long ago the agent reported its context, if it ever has. */
	function reportedAgo(at: number | null): string {
		return at === null ? '' : since(at);
	}

	/** What a thread is in, so the picker says whether it is still live. */
	function threadState(comment: Thread): string {
		if (comment.anchor.outdated) return 'outdated';
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
	// Asked for from the keyboard, perhaps before the panel was open: taken
	// once the field is drawn
	$effect(() => {
		if (!composer || !review.layout.agentPanel.inputWanted) return;
		composer.focus();
		review.layout.agentPanel.inputTaken();
	});

	// A new turn is the point of the panel, so it is brought into view. The
	// count is what this watches: it changes exactly when something is said.
	$effect(() => {
		const said = review.conversation.turns.length;
		if (said === 0 || !stream || !atFoot) return;
		const shown = stream;
		requestAnimationFrame(() => {
			// Asked again: the reader may have scrolled away in the frame it
			// took the turn to be laid out
			if (atFoot) shown.scrollTop = shown.scrollHeight;
		});
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
		review.conversation.composer.setText(field.value);
		const opening = /@([^\s@]*)$/.exec(field.value.slice(0, field.selectionStart));
		picking = opening !== null;
		query = opening?.[1] ?? '';
		highlighted = 0;
	}

	/** Put the token where the @ was, and carry on typing. */
	function take(pick: Candidate) {
		const field = composer;
		if (!field) return;
		const caret = field.selectionStart;
		const before = draft.slice(0, caret).replace(/@[^\s@]*$/, '');
		const after = draft.slice(caret);
		const token = `${pick.kind === 'thread' ? anchorToken(pick.comment.anchor) : `@${pick.path}`} `;
		review.conversation.composer.setText(`${before}${token}${after}`);
		picking = false;
		field.focus();
		requestAnimationFrame(() => {
			const at = before.length + token.length;
			field.setSelectionRange(at, at);
		});
	}

	/** Take a thread out of the message by taking its token out of the words. */
	function drop(comment: Thread) {
		review.conversation.composer.setText(draft.split(anchorToken(comment.anchor)).join('').replace(/ {2,}/g, ' '));
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

	async function onPaste(event: ClipboardEvent) {
		const refusal = await review.conversation.composer.attachments.takePaste(event, review.limits);
		if (refusal) failed = refusal;
	}

	/**
	 * An image that cannot be drawn: most often a review restarted under the
	 * draft, but a file the browser cannot decode looks the same from here.
	 */
	function onImageLost(imageId: string) {
		review.conversation.composer.attachments.forget(imageId);
		failed = 'An image could not be shown and was taken off the message';
	}

	async function send() {
		if (!sayable || sending || review.conversation.composer.attachments.uploading > 0 || !attached) return;
		sending = true;
		failed = null;
		// Sending is a deliberate act: it always brings you back to the foot
		atFoot = true;
		try {
			await review.conversation.send(pointed);
			picking = false;
		} catch (error) {
			failed = messageOf(error, SENDING_FAILED);
		} finally {
			sending = false;
		}
	}

	async function stop(messageId: string) {
		failed = null;
		try {
			await review.conversation.cancel(messageId);
		} catch (error) {
			failed = messageOf(error, STOPPING_FAILED);
		}
	}

	/** The panel is on the right, so dragging left is what widens it. */
	const sizing = $derived({
		width: review.layout.agentPanel.width,
		grows: 'left' as const,
		onWidth: (width: number) => review.layout.agentPanel.setWidth(width)
	});
</script>

{#snippet workUnderWay()}
	<!-- What is being done, in its own words, replaced as it changes -->
	{#if review.answerer.work?.text}
		<p data-testid="panel-progress" class="cr-progress text-sm">
			{review.answerer.work.text}
		</p>
	{/if}
	{#if review.answerer.work && review.answerer.work.steps.length > 0}
		<!-- Branches of the same work, drawn hanging off it -->
		<ul data-testid="progress-steps" class="cr-branches">
			{#each review.answerer.work.steps as step (step.text)}
				<li class="cr-branch {step.done ? 'cr-branch-done' : ''}">
					{#if step.done}
						<Icon name="check" class="cr-branch-mark" />
					{:else}
						<span class="cr-branch-mark"><span class="cr-dot"></span></span>
					{/if}
					<span>{step.text}</span>
				</li>
			{/each}
		</ul>
	{/if}
	{#if review.answerer.work && review.answerer.work.files.length > 0}
		<div class="flex flex-wrap gap-1">
			{#each review.answerer.work.files as path (path)}
				<button data-testid="progress-file" class="cr-thread-chip" onclick={() => review.sections.showFile(path)}>
					{path.split('/').pop()}
				</button>
			{/each}
		</div>
	{/if}
{/snippet}

<aside
	data-testid="agent-panel"
	data-tour="agent-panel"
	class="cr-panel flex min-h-0 shrink-0 flex-col border-l border-base-300"
	style="width: {review.layout.agentPanel.width}px"
>
	<EdgeGrip {sizing} label="Resize the panel" testId="panel-resize" />

	<header
		data-testid="panel-status"
		class="flex h-9 shrink-0 items-center gap-2 border-b border-base-300 bg-base-200 px-3"
	>
		<span
			class="h-1.5 w-1.5 shrink-0 rounded-full"
			style="background: {attached ? (working ? 'var(--cr-mark)' : 'var(--cr-add-edge)') : 'var(--color-base-300)'}"
		></span>
		<span class="text-sm font-semibold {attached ? '' : 'cr-muted'}">
			{attached ? 'Agent' : 'Waiting for the agent'}
		</span>
		{#if review.answerer.status.model}
			<span data-testid="agent-model" class="cr-faint font-mono text-xs">
				{review.answerer.status.model}
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
			onclick={() => review.layout.agentPanel.setOpen(false)}
		>
			<Icon name="chevron" class="h-3 w-3 -rotate-90" />
		</button>
	</header>

	<!-- Two numbers, told apart: one this side measures, one the agent reports -->
	<div class="flex shrink-0 flex-wrap items-center gap-2 border-b border-base-300 px-3 py-1.5">
		<span data-testid="review-weight" class="cr-pill" title="What handing this review over costs">
			review {formatWeight(review.weight)}
		</span>
		{#if review.answerer.status.context}
			<span data-testid="agent-context" class="cr-pill">
				context {review.answerer.status.context} · as reported {reportedAgo(review.answerer.status.at)}
			</span>
		{/if}
	</div>

	<div
		data-testid="panel-turns"
		bind:this={stream}
		onscroll={onScroll}
		class="min-h-0 flex-1 overflow-y-auto px-3 py-3"
	>
		<!-- Work showing outranks the empty state: an agent doing something
			before anybody has said anything is exactly the case a reader has
			no other way of seeing. -->
		{#if review.conversation.turns.length === 0 && !review.answerer.work}
			{#if attached}
				<div data-testid="panel-empty" class="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
					<Icon name="conversation" class="h-5 w-5" style="color: var(--color-base-300)" />
					<p class="cr-faint text-sm leading-relaxed">
						Ask about anything — the plan, the tests, a file nobody commented on. A thread is about one line; this is
						about the rest.
					</p>
				</div>
			{:else}
				<!-- Before the agent's first wait this is what the reader sees, and
					an agent that opened the review is seconds away from it. So the
					state reads as waiting; how to attach one by hand is only for
					whoever started the review themselves. -->
				<div
					data-testid="panel-unattached"
					class="flex h-full flex-col items-center justify-center gap-3 px-4 text-center"
				>
					<p class="cr-faint text-sm leading-relaxed">
						The agent joins once it starts listening. Comments you write meanwhile are kept.
					</p>
					<details data-testid="panel-attach-by-hand" class="w-full text-left">
						<summary class="cr-faint cursor-pointer text-center text-xs"> Started the review yourself? </summary>
						<p class="cr-faint mt-2 text-xs leading-relaxed">
							Nothing answers a review run in the foreground. Start it in the background and keep the listening half in
							a loop:
						</p>
						<pre
							class="cr-code cr-muted mt-2 w-full overflow-x-auto rounded border border-base-300 bg-base-200 px-3 py-2">claude-review diff --no-open &
claude-review wait --port &lt;port&gt; --until-event</pre>
					</details>
				</div>
			{/if}
		{:else}
			<div class="flex flex-col gap-3">
				{#each review.conversation.turns as turn (turn.id)}
					{#if turn.author === 'event'}
						{@const raised = review.threads.all.find((c) => c.id === turn.threads?.[0])}
						<div data-testid="panel-event" class="cr-round-mark">
							<span></span>
							{#if raised}
								<button
									data-testid="panel-thread-ref"
									class="cr-thread-chip"
									onclick={() => review.navigator.reveal(raised)}
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
							<p class="cr-who"><strong>You</strong> {clockTime(turn.at)}</p>
							{#if turn.body}
								<MarkdownRenderer text={turn.body} dense />
							{/if}
							<SaidImages images={turn.images ?? []} />
							{#if turn.threads && turn.threads.length > 0}
								<div class="mt-2 flex flex-wrap gap-1">
									{#each turn.threads as id (id)}
										{@const thread = review.threads.all.find((c) => c.id === id)}
										{#if thread}
											<button
												data-testid="panel-thread-ref"
												class="cr-thread-chip"
												onclick={() => review.navigator.reveal(thread)}
											>
												{anchorShortPlace(thread.anchor)}
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
							<p class="cr-who"><strong>Agent</strong> {clockTime(turn.at)}</p>
							<MarkdownRenderer text={turn.body} dense />
							{#if turn.files && turn.files.length > 0}
								<div class="mt-2 flex flex-wrap gap-1">
									{#each turn.files as path (path)}
										<button
											data-testid="answer-file"
											class="cr-thread-chip"
											onclick={() => review.sections.showFile(path)}
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
							<span class="cr-who"><strong>Agent</strong></span>
							<TypingIndicator />
							<div class="flex-1"></div>
							<span class="cr-faint text-xs">working {since(working.at)}</span>
							<button data-testid="stop-message" class="btn btn-outline btn-xs" onclick={() => stop(working.id)}>
								Stop
							</button>
						</div>
						{@render workUnderWay()}
					</div>
				{:else if review.answerer.work}
					<!-- Work nobody is waiting on: what a round asked for, or what
						the agent took on itself. Without a row of its own it could not
						be shown at all, and a reader watching a silent panel cannot
						tell work from a hang. -->
					<div data-testid="panel-work" class="cr-answer flex flex-col gap-2">
						<div class="flex items-center gap-3">
							<span class="cr-who"><strong>Agent</strong></span>
							<TypingIndicator />
							<div class="flex-1"></div>
							<span class="cr-faint text-xs">working {since(review.answerer.work.at)}</span>
						</div>
						{@render workUnderWay()}
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<div class="relative shrink-0 border-t border-base-300 px-3 py-2">
		{#if picking && candidates.length > 0}
			<div data-testid="thread-picker" class="cr-picker">
				{#each candidates as pick, index (pick.kind === 'thread' ? pick.comment.id : pick.path)}
					<button
						data-testid={pick.kind === 'thread' ? 'thread-option' : 'file-option'}
						class="cr-picker-row {index === highlighted ? 'cr-picker-on' : ''}"
						onclick={() => take(pick)}
					>
						<span class="cr-comment-ref block truncate font-mono text-xs">
							{pick.kind === 'thread' ? anchorShortPlace(pick.comment.anchor) : pick.path}
						</span>
						{#if pick.kind === 'thread'}
							<span class="cr-muted block truncate text-sm">
								{pick.comment.body}{threadState(pick.comment) ? ` · ${threadState(pick.comment)}` : ''}
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
							{anchorShortPlace(comment.anchor)}
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
			<AttachedImages attachments={review.conversation.composer.attachments} disabled={sending} onLost={onImageLost} />
			<textarea
				data-testid="panel-input"
				bind:this={composer}
				class="cr-field cr-comment-body w-full resize-y rounded px-3 py-2"
				rows="2"
				placeholder="Ask about anything, or paste a screenshot…"
				value={draft}
				oninput={onInput}
				onkeydown={onKeydown}
				onpaste={onPaste}
			></textarea>
			<div class="mt-2 flex items-center gap-2">
				<button data-testid="mention-thread" class="btn btn-ghost btn-xs" onclick={openPicker}>
					@ thread or file
				</button>
				<span class="cr-faint hidden text-xs lg:inline">Ctrl+Enter sends</span>
				<div class="flex-1"></div>
				{#if failed}
					<span data-testid="panel-error" class="text-xs text-error">{failed}</span>
				{/if}
				<button
					data-testid="send-message"
					class="btn btn-primary btn-xs"
					disabled={!sayable || sending || review.conversation.composer.attachments.uploading > 0}
					onclick={send}
				>
					{sending ? 'Sending' : 'Send'}
				</button>
			</div>
		{:else}
			<p data-testid="panel-read-only" class="cr-faint py-1 text-center text-xs">
				You can write here once the agent is listening.
			</p>
		{/if}
	</div>
</aside>
