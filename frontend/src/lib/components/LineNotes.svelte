<script lang="ts">
	import type { LinePlace } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import CommentBox from './CommentBox.svelte';
	import CommentThread from './CommentThread.svelte';
	import type { LineCommenting } from './line-commenting.svelte';

	interface Props {
		commenting: LineCommenting;
		/** The line they hang under. */
		place: LinePlace;
	}

	let { commenting, place }: Props = $props();
	const review = useReview();
</script>

<!-- What hangs under a line: its threads, and the comment being written there -->
{#each commenting.threadsUnder(place) as thread (thread.id)}
	<CommentThread comment={thread} />
{/each}
{#if commenting.opensUnder(place)}
	<div class="px-3 py-2">
		<CommentBox
			kind="new"
			onSave={(body, severity, images) => commenting.save(body, severity, images)}
			onAsk={review.answerer.attached ? (body, severity, images) => commenting.ask(body, severity, images) : undefined}
			onCancel={() => commenting.cancel()}
			label={commenting.label}
			suggestFrom={commenting.quote}
		/>
	</div>
{/if}
