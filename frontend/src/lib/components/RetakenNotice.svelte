<script lang="ts">
	import type { FollowOutcome } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import { followWords, PHRASE_BREAK } from '$lib/review/follow-words';
	import { counted, wordsFor } from '$lib/utils/words';
	import { Attempt } from './attempt.svelte';
	import NoticeBar from './NoticeBar.svelte';

	interface Props {
		/** What following the threads onto the diff taken again did to them. */
		retaken: FollowOutcome;
	}

	// What the way to the thread that lost its lines says: of the one, or of the first of several
	const SHOW_OUTDATED = { one: 'Show the outdated thread', many: 'Show the first outdated thread' };

	let { retaken }: Props = $props();
	const review = useReview();
	const showing = new Attempt();

	// The one thing a retake can lose: a thread whose lines are gone. It keeps
	// what it was written against, and that is what the button goes to: the
	// first, when there are several.
	const outdated = $derived(review.threads.all.filter((thread) => thread.anchor.outdated));
	const stranded = $derived(outdated.at(0));

	/** What the retaken bar says happened, in the order it matters. */
	function whatChanged(): string {
		const count = review.lastRetake.changedCount;
		const since = review.lastRetake.changedSince;
		if (!review.lastRetake.changedKnown) {
			// Every tick has just been dropped, and saying "nothing changed"
			// here would be the opposite of what the reader must do next
			return 'Diff retaken — what changed could not be worked out, so nothing is marked read';
		}
		if (since === null) return 'Diff retaken';
		if (count === 0) return `Diff retaken — nothing has changed since round ${since}`;
		return `Diff retaken — ${counted(count, 'file has', 'files have')} changed since round ${since}`;
	}

	async function showWhatChanged() {
		if (await showing.run(() => review.showChangesSinceRetake())) review.lastRetake.dismiss();
	}
</script>

<!-- Says what happened to the threads, because that is what the reader
	stands to lose in a retake -->
<NoticeBar testId="diff-retaken" kind="cr-notice-taken" icon="check">
	{[whatChanged(), ...followWords(retaken)].join(PHRASE_BREAK)}
	{#snippet actions()}
		{#if showing.failed}
			<span data-testid="retaken-error" class="text-error">{showing.failed}</span>
		{/if}
		{#if review.lastRetake.changedSince !== null && review.lastRetake.changedCount > 0}
			<button type="button" data-testid="show-what-changed" class="btn btn-ghost btn-xs" onclick={showWhatChanged}>
				Show what changed
			</button>
		{/if}
		{#if stranded}
			<button
				type="button"
				data-testid="show-outdated"
				class="btn btn-ghost btn-xs"
				onclick={() => review.navigator.reveal(stranded)}
			>
				{wordsFor(outdated.length, SHOW_OUTDATED)}
			</button>
		{/if}
		<button
			type="button"
			data-testid="dismiss-retaken"
			class="btn btn-ghost btn-xs"
			onclick={() => review.lastRetake.dismiss()}
		>
			Dismiss
		</button>
	{/snippet}
</NoticeBar>
