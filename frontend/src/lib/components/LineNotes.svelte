<script lang="ts">
	import type { LinePlace, WrittenOnLines } from '$lib/types';
	import { lineRangeLabel } from '$lib/anchors/line-label';
	import type { CommentField } from '$lib/review/comment-field.svelte';
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

	/** Where a comment being written hangs, said above its field. */
	function labelOf(field: CommentField<WrittenOnLines>): string {
		const { side, startLine, endLine } = field.at.lines;
		return lineRangeLabel(side, startLine, endLine);
	}

	/** Add a comment and hand it straight to whoever is answering. */
	async function askNow(field: CommentField<WrittenOnLines>) {
		try {
			await review.threads.sayAndAsk(field);
		} catch {
			// The comment is written either way; the thread offers to ask again
		}
	}
</script>

<!-- What hangs under a line: its threads, and the comments being written there -->
{#each commenting.threadsUnder(place) as thread (thread.id)}
	<CommentThread {thread} />
{/each}
{#each commenting.fieldsUnder(place) as field (field.key)}
	<div class="px-3 py-2">
		<CommentBox
			{field}
			onSave={() => review.threads.say(field)}
			onAsk={review.answerer.attached ? () => askNow(field) : undefined}
			onCancel={() => review.threads.writing.discard(field)}
			label={labelOf(field)}
			suggestFrom={field.at.quote}
		/>
	</div>
{/each}
