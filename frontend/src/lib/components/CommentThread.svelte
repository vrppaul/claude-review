<script lang="ts">
	import type { Comment, CommentSeverity } from '$lib/types';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { discussionStore } from '$lib/stores/discussion.svelte';
	import { lineRangeLabel } from '$lib/utils/line-label';
	import { splitSuggestions } from '$lib/utils/suggestion';
	import CommentBox from './CommentBox.svelte';

	interface Props {
		comment: Comment;
		/** The lines the comment covers, sent along with a question. */
		quote?: string[];
	}

	let { comment, quote = [] }: Props = $props();
	let editing = $state(false);
	let asking = $state(false);
	let question = $state('');
	let askFailed = $state<string | null>(null);

	const talk = $derived(discussionStore.forThread(comment.id));

	async function ask() {
		if (!question.trim()) return;
		askFailed = null;
		try {
			await discussionStore.ask(comment, quote, question.trim());
			asking = false;
			question = '';
		} catch (e) {
			askFailed = e instanceof Error ? e.message : 'Could not ask';
		}
	}

	function handleSave(body: string, severity: CommentSeverity) {
		commentStore.update(comment.id, body, severity);
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
			initialSeverity={comment.severity}
			side={comment.side}
			startLine={comment.start_line}
			endLine={comment.end_line}
		/>
	{:else}
		<div class="cr-comment group rounded-r px-4 py-3">
			<div class="flex items-baseline gap-3">
				<span data-testid="comment-line-label" class="cr-comment-ref font-mono text-xs">
					{label}
				</span>
				{#if comment.severity !== 'note'}
					<span data-testid="comment-severity" class="cr-severity cr-severity-{comment.severity}"
						>{comment.severity}</span
					>
				{/if}
				<div class="flex-1"></div>
				<div
					class="flex gap-1 opacity-45 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
				>
					<button
						data-testid="edit-comment"
						class="btn btn-ghost btn-xs"
						onclick={() => (editing = true)}
					>
						Edit
					</button>
					<button
						data-testid="ask-claude"
						class="btn btn-ghost btn-xs"
						onclick={() => (asking = !asking)}
					>
						Ask Claude
					</button>
					<button
						data-testid="delete-comment"
						class="btn btn-ghost btn-xs hover:text-error"
						onclick={() => commentStore.remove(comment.id)}
					>
						Delete
					</button>
				</div>
			</div>
			{#each splitSuggestions(comment.body) as part, i (i)}
				{#if part.kind === 'suggestion'}
					<pre
						data-testid="comment-suggestion"
						class="mt-2 overflow-x-auto rounded bg-base-100 p-3 font-mono text-xs">{part.text}</pre>
				{:else}
					<p class="cr-comment-body mt-1 whitespace-pre-wrap">{part.text}</p>
				{/if}
			{/each}

			{#if asking}
				<div class="mt-3 space-y-2 border-t border-base-300 pt-3">
					<textarea
						data-testid="ask-input"
						class="cr-comment-body textarea min-h-16 w-full bg-base-100 focus:outline-none"
						placeholder="Ask Claude about this — it keeps reading while you write"
						bind:value={question}
					></textarea>
					<div class="flex items-center gap-2">
						{#if askFailed}
							<span data-testid="ask-error" class="text-xs text-error">{askFailed}</span>
						{/if}
						<div class="flex-1"></div>
						<button class="btn btn-ghost btn-xs" onclick={() => (asking = false)}>Cancel</button>
						<button
							class="btn btn-primary btn-xs"
							data-testid="send-question"
							disabled={!question.trim()}
							onclick={ask}
						>
							Ask
						</button>
					</div>
				</div>
			{/if}

			{#if talk}
				<div data-testid="thread-talk" class="mt-3 border-t border-base-300 pt-3">
					<p class="cr-comment-body cr-muted whitespace-pre-wrap">{talk.asked}</p>
					{#if talk.answer === null}
						<p data-testid="awaiting-answer" class="cr-muted mt-2 text-xs">
							Waiting for Claude…
						</p>
					{:else}
						<p data-testid="thread-answer" class="cr-comment-body mt-2 whitespace-pre-wrap">
							{talk.answer}
						</p>
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</div>
