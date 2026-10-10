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

<!-- What hangs under a line: its threads, and the comments being written there -->
{#each commenting.threadsUnder(place) as thread (thread.id)}
	<CommentThread comment={thread} />
{/each}
{#each commenting.fieldsUnder(place) as field (field.key)}
	<div class="px-3 py-2">
		<CommentBox
			{field}
			onSave={(body, severity, images) => commenting.save(field, body, severity, images)}
			onAsk={review.answerer.attached
				? (body, severity, images) => commenting.ask(field, body, severity, images)
				: undefined}
			onCancel={() => commenting.cancel(field)}
			label={commenting.labelOf(field)}
			suggestFrom={commenting.quoteOf(field)}
		/>
	</div>
{/each}
