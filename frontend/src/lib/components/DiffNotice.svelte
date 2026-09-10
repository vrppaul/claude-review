<script lang="ts">
	import { commentStore } from '$lib/stores/comments.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { scrollToComment } from '$lib/utils/scroll';

	let failed = $state<string | null>(null);

	// How long the retaken bar stands. Long enough to read twice, short
	// enough that it is not still there when the reader looks up again — it
	// reports something that already happened and needs no answer.
	const SHOWN_FOR = 12_000;

	const moved = $derived(diffStore.movedFiles);
	const retaken = $derived(diffStore.retaken);
	// The one thing a retake can lose: a thread whose lines are gone. It keeps
	// what it was written against, and that is what "show it" goes to.
	const stranded = $derived(commentStore.comments.find((comment) => comment.outdated));

	// Each retake starts the clock afresh: what it says is about that one
	$effect(() => {
		if (!diffStore.retaken) return;
		const timer = setTimeout(() => diffStore.dismissRetaken(), SHOWN_FOR);
		return () => clearTimeout(timer);
	});

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
			Diff retaken{retaken.followed > 0
				? ` · ${retaken.followed} ${retaken.followed === 1 ? 'thread' : 'threads'} followed their lines`
				: ''}{retaken.outdated > 0
				? ` · ${retaken.outdated} ${retaken.outdated === 1 ? 'is' : 'are'} outdated`
				: ''}
		</span>
		<div class="flex-1"></div>
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
{/if}
