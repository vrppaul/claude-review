<script lang="ts">
	import type { Comment } from '$lib/types';
	import { commentStore } from '$lib/stores/comments.svelte';
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

	function lineRef(): string {
		if (comment.start_line === comment.end_line) {
			return `${comment.start_line}`;
		}
		return `${comment.start_line}-${comment.end_line}`;
	}
</script>

<div id={comment.id} class="bg-warning/10 border border-warning/30 rounded-lg p-4">
	{#if editing}
		<CommentBox
			onSave={handleSave}
			onCancel={() => (editing = false)}
			initialBody={comment.body}
			startLine={comment.start_line}
			endLine={comment.end_line}
		/>
	{:else}
		<div class="flex items-start justify-between gap-2">
			<div class="flex-1">
				<span class="text-xs text-warning font-mono font-semibold">Line {lineRef()}</span>
				<p class="text-sm whitespace-pre-wrap">{comment.body}</p>
			</div>
			<div class="flex gap-0.5">
				<button class="btn btn-ghost btn-xs" onclick={() => (editing = true)}>Edit</button>
				<button class="btn btn-ghost btn-xs text-error" onclick={() => commentStore.remove(comment.id)}>
					Delete
				</button>
			</div>
		</div>
	{/if}
</div>
