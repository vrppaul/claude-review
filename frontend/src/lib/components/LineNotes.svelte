<script lang="ts">
	import type { LinePlace, WrittenOnLines } from '$lib/types';
	import { lineRangeLabel } from '$lib/anchors/line-label';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { useReview } from '$lib/review/context';
	import { placeKey } from '$lib/utils/line-places';
	import CommentBox from './CommentBox.svelte';
	import CommentThread from './CommentThread.svelte';
	import { askComment, sayComment } from './comment-endings';
	import type { LineCommenting } from './line-commenting.svelte';

	interface Props {
		commenting: LineCommenting;
		/** The line they hang under. */
		place: LinePlace;
	}

	let { commenting, place }: Props = $props();
	const review = useReview();

	/** Where a comment being written hangs, said above its field. */
	function labelOf(field: CommentField<WrittenOnLines>): string {
		const { side, startLine, endLine } = field.at.lines;
		return lineRangeLabel(side, startLine, endLine);
	}

	/** Put a comment away unsaid; the keyboard goes back to the line it was opened under. */
	function putAway(field: CommentField<WrittenOnLines>) {
		review.threads.writing.discard(field);
		review.sections.keyboardToLine(field.at.file, placeKey(field.at.lines.opensBelow));
	}
</script>

<!-- What hangs under a line: its threads, and the comments being written there -->
{#each commenting.threadsUnder(place) as thread (thread.id)}
	<CommentThread {thread} />
{/each}
{#each commenting.fieldsUnder(place) as field (field.key)}
	<div class="cr-thread-hang">
		<CommentBox
			{field}
			onSave={() => sayComment(review, field)}
			onAsk={review.canAsk ? () => askComment(review, field) : undefined}
			onCancel={() => putAway(field)}
			label={labelOf(field)}
			suggestFrom={field.at.quote}
		/>
	</div>
{/each}
