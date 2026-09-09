<script lang="ts">
	import type { Comment } from '$lib/types';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { lineRangeLabel } from '$lib/utils/line-label';
	import CommentBox from './CommentBox.svelte';

	interface Props {
		comment: Comment;
	}

	let { comment }: Props = $props();
	let editing = $state(false);

	function handleSave(body: string) {
		commentStore.update(comment.id, body);
		editing = false;
	}

	const label = $derived(lineRangeLabel(comment.side, comment.start_line, comment.end_line));
</script>

<div id={comment.id} class="px-3 py-2">
	{#if editing}
		<CommentBox
			onSave={handleSave}
			onCancel={() => (editing = false)}
			initialBody={comment.body}
			side={comment.side}
			startLine={comment.start_line}
			endLine={comment.end_line}
		/>
	{:else}
		<div class="cr-comment rounded-r px-4 py-3">
			<div class="flex items-baseline gap-3">
				<span data-testid="comment-line-label" class="cr-comment-ref font-mono text-xs">
					{label}
				</span>
				<div class="flex-1"></div>
				<button
					data-testid="edit-comment"
					class="btn btn-ghost btn-xs"
					onclick={() => (editing = true)}
				>
					Edit
				</button>
				<button
					data-testid="delete-comment"
					class="btn btn-ghost btn-xs hover:text-error"
					onclick={() => commentStore.remove(comment.id)}
				>
					Delete
				</button>
			</div>
			<p class="cr-comment-body mt-1 whitespace-pre-wrap">{comment.body}</p>
		</div>
	{/if}
</div>
