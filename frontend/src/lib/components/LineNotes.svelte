<script lang="ts">
	import type { LinePlace, WrittenOnLines } from '$lib/types';
	import { lineRangeLabel } from '$lib/anchors/line-label';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { useReview } from '$lib/review/context';
	import { placeKey } from '$lib/utils/line-places';
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

	/** Add a comment; the keyboard goes on to the thread it became. */
	function add(field: CommentField<WrittenOnLines>) {
		review.sections.keyboardToThread(review.threads.say(field));
	}

	/** Add a comment and hand it straight to whoever is answering; the keyboard goes on to its thread. */
	async function askNow(field: CommentField<WrittenOnLines>) {
		const said = review.threads.sayAndAsk(field);
		review.sections.keyboardToThread(said.thread);
		try {
			await said.asked;
		} catch {
			// The comment is written either way; the thread offers to ask again
		}
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
	<div class="px-3 py-2">
		<CommentBox
			{field}
			onSave={() => add(field)}
			onAsk={review.canAsk ? () => askNow(field) : undefined}
			onCancel={() => putAway(field)}
			label={labelOf(field)}
			suggestFrom={field.at.quote}
		/>
	</div>
{/each}
