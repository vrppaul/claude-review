<script lang="ts">
	import type { Comment } from '$lib/types';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { lineRangeLabel } from '$lib/utils/line-label';
	import { isDrawn } from '$lib/utils/placement';
	import { scrollToComment } from '$lib/utils/scroll';

	let failed = $state<string | null>(null);

	// How long the retaken bar stands. Long enough to read twice, short
	// enough that it is not still there when the reader looks up again — it
	// reports something that already happened and needs no answer.
	const SHOWN_FOR = 12_000;

	const moved = $derived(diffStore.movedFiles);
	const retaken = $derived(diffStore.retaken);
	// Threads the base on screen cannot draw. They are not lost — they are
	// anchored to the review's own diff — but saying nothing would leave the
	// reader counting a review they can only see part of.
	const offScreen = $derived(
		commentStore.comments.filter((c) => !isDrawn(c, diffStore.files, { removedLines: false }))
	);
	let listing = $state(false);

	/** Take the reader back to the whole diff, and to the thread they picked. */
	async function goTo(comment: Comment) {
		failed = null;
		try {
			await diffStore.setBase('review');
			listing = false;
			requestAnimationFrame(() => scrollToComment(comment.id, comment.file));
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not take the whole diff again';
		}
	}
	// The one thing a retake can lose: a thread whose lines are gone. It keeps
	// what it was written against, and that is what "show it" goes to.
	const stranded = $derived(commentStore.comments.find((comment) => comment.outdated));

	// Each retake starts the clock afresh: what it says is about that one
	$effect(() => {
		if (!diffStore.retaken) return;
		const timer = setTimeout(() => diffStore.dismissRetaken(), SHOWN_FOR);
		return () => clearTimeout(timer);
	});

	/** What the retaken bar says happened, in the order it matters. */
	function whatChanged(): string {
		const count = diffStore.changedCount;
		const since = diffStore.changedSince;
		if (!diffStore.changedKnown) {
			// Every tick has just been dropped, and saying "nothing changed"
			// here would be the opposite of what the reader must do next
			return 'Diff retaken — what changed could not be worked out, so nothing is marked read';
		}
		if (since === null) return 'Diff retaken';
		if (count === 0) return `Diff retaken — nothing has changed since round ${since}`;
		return `Diff retaken — ${count} ${count === 1 ? 'file has' : 'files have'} changed since round ${since}`;
	}

	async function showWhatChanged() {
		failed = null;
		try {
			await diffStore.setBase(`round:${diffStore.changedSince}`);
			diffStore.dismissRetaken();
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not take the diff against that round';
		}
	}

	async function showEverything() {
		failed = null;
		try {
			await diffStore.setBase('review');
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not take the whole diff again';
		}
	}

	async function retake() {
		failed = null;
		try {
			await diffStore.retake();
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not take the diff again';
		}
	}
</script>

{#if moved > 0}
	<!-- Amber, not the mark colour: this is the code moving, not the reader's
		own mark. Never a swap: whoever is mid-sentence decides when. -->
	<div
		data-testid="tree-moved"
		class="cr-notice cr-notice-moved flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
	>
		<svg
			class="h-3 w-3 shrink-0"
			viewBox="0 0 16 16"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			stroke-linecap="round"
			aria-hidden="true"
		>
			<path d="M8 4.5v4"></path>
			<path d="M8 11.2v.3"></path>
			<circle cx="8" cy="8" r="6"></circle>
		</svg>
		<span>
			The working tree has moved on — {moved}
			{moved === 1 ? 'file has' : 'files have'} changed since this diff was taken.
		</span>
		<div class="flex-1"></div>
		{#if failed}
			<span data-testid="retake-error" class="text-error">{failed}</span>
		{/if}
		<button data-testid="retake-diff" class="btn btn-ghost btn-xs" onclick={retake}>Retake</button>
		<button
			data-testid="dismiss-moved"
			class="btn btn-ghost btn-xs"
			onclick={() => diffStore.dismissMoved()}
		>
			Dismiss
		</button>
	</div>
{:else if retaken}
	<!-- Says what happened to the threads, because that is what the reader
		stands to lose in a retake -->
	<div
		data-testid="diff-retaken"
		class="cr-notice cr-notice-taken flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
	>
		<svg
			class="h-3 w-3 shrink-0"
			viewBox="0 0 16 16"
			fill="none"
			stroke="currentColor"
			stroke-width="1.6"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<path d="M3 8.5l3.2 3.2L13 5"></path>
		</svg>
		<span>
			{whatChanged()}{retaken.followed > 0
				? ` · ${retaken.followed} ${retaken.followed === 1 ? 'thread' : 'threads'} followed their lines`
				: ''}{retaken.outdated > 0
				? ` · ${retaken.outdated} ${retaken.outdated === 1 ? 'is' : 'are'} outdated`
				: ''}
		</span>
		<div class="flex-1"></div>
		{#if failed}
			<span data-testid="retaken-error" class="text-error">{failed}</span>
		{/if}
		{#if diffStore.changedSince !== null && diffStore.changedCount > 0}
			<button
				data-testid="show-what-changed"
				class="btn btn-ghost btn-xs"
				onclick={showWhatChanged}
			>
				Show what changed
			</button>
		{/if}
		{#if stranded}
			<button
				data-testid="show-outdated"
				class="btn btn-ghost btn-xs"
				onclick={() => scrollToComment(stranded.id, stranded.file)}
			>
				Show it
			</button>
		{/if}
		<button
			data-testid="dismiss-retaken"
			class="btn btn-ghost btn-xs"
			onclick={() => diffStore.dismissRetaken()}
		>
			Dismiss
		</button>
	</div>

	{#if listing}
		<!-- Where they are, so a count is not the end of the road. Picking one
			puts the whole diff back and goes to it: it is anchored there, and
			that is the only screen that can draw it. -->
		<div
			data-testid="off-screen-list"
			class="shrink-0 border-b border-base-300 bg-base-100 px-4 py-1.5"
		>
			{#each offScreen as comment (comment.id)}
				<button
					data-testid="off-screen-thread"
					class="flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-base-200"
					onclick={() => goTo(comment)}
				>
					<span class="cr-comment-ref shrink-0 font-mono text-xs">
						{comment.file.split('/').pop()}
						{lineRangeLabel(comment.side, comment.start_line, comment.end_line)}
					</span>
					<span class="cr-faint min-w-0 flex-1 truncate text-xs">{comment.body}</span>
				</button>
			{/each}
			<p class="cr-faint px-2 pt-1 text-xs">
				They are still in the review, and still go out with the round.
			</p>
		</div>
	{/if}
{/if}

{#if diffStore.narrowed}
	<!-- A state, not news: no Dismiss, because dismissing it would leave the
		reader looking at part of the review with nothing saying so. The way
		out is the only other thing here. -->
	<div
		data-testid="narrowed-to"
		class="cr-notice cr-notice-taken flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
	>
		<svg
			class="h-3 w-3 shrink-0"
			viewBox="0 0 16 16"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<path d="M2.5 5h9"></path>
			<path d="M9 2.5L11.5 5 9 7.5"></path>
			<path d="M13.5 11h-9"></path>
			<path d="M7 8.5L4.5 11 7 13.5"></path>
		</svg>
		<span>
			{#if diffStore.files.length === 0}
				Nothing has changed — {diffStore.phrase}.
			{:else}
				Showing {diffStore.phrase} — {diffStore.files.length}
				{diffStore.files.length === 1 ? 'file' : 'files'}.
			{/if}
			{#if offScreen.length > 0}
				{offScreen.length}
				{offScreen.length === 1 ? 'thread is' : 'threads are'} not on this screen.
			{/if}
		</span>
		<div class="flex-1"></div>
		{#if failed}
			<span data-testid="narrow-error" class="text-error">{failed}</span>
		{/if}
		{#if offScreen.length > 0}
			<button
				data-testid="list-off-screen"
				class="btn btn-ghost btn-xs"
				aria-expanded={listing}
				onclick={() => (listing = !listing)}
			>
				{listing ? 'Hide them' : 'List them'}
			</button>
		{/if}
		<button data-testid="show-everything" class="btn btn-ghost btn-xs" onclick={showEverything}>
			Show the whole diff
		</button>
	</div>

	{#if listing}
		<!-- Where they are, so a count is not the end of the road. Picking one
			puts the whole diff back and goes to it: it is anchored there, and
			that is the only screen that can draw it. -->
		<div
			data-testid="off-screen-list"
			class="shrink-0 border-b border-base-300 bg-base-100 px-4 py-1.5"
		>
			{#each offScreen as comment (comment.id)}
				<button
					data-testid="off-screen-thread"
					class="flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-base-200"
					onclick={() => goTo(comment)}
				>
					<span class="cr-comment-ref shrink-0 font-mono text-xs">
						{comment.file.split('/').pop()}
						{lineRangeLabel(comment.side, comment.start_line, comment.end_line)}
					</span>
					<span class="cr-faint min-w-0 flex-1 truncate text-xs">{comment.body}</span>
				</button>
			{/each}
			<p class="cr-faint px-2 pt-1 text-xs">
				They are still in the review, and still go out with the round.
			</p>
		</div>
	{/if}
{/if}
