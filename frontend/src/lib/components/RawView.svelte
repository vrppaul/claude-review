<script lang="ts">
	import type { DiffFile, DiffLine } from '$lib/types';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { highlightLine } from '$lib/utils/highlight';
	import { createLineSelection } from '$lib/utils/line-selection.svelte';
	import CommentBox from './CommentBox.svelte';
	import CommentThread from './CommentThread.svelte';

	interface Props {
		file: DiffFile;
		language: string | null;
	}

	let { file, language }: Props = $props();

	const isDiffMode = $derived(diffStore.mode === 'diff');
	const colSpan = $derived(isDiffMode ? 4 : 2);
	const selection = createLineSelection();

	// Compute flat line index offsets per hunk so we have unique indices across all hunks
	const hunkOffsets = $derived(
		file.hunks.reduce<number[]>((acc, hunk, i) => {
			acc.push(i === 0 ? 0 : acc[i - 1] + file.hunks[i - 1].lines.length);
			return acc;
		}, [])
	);

	$effect(() => {
		void file.path;
		selection.reset();
	});

	// Window-level listener so mouseup is caught even if the cursor
	// leaves this component (e.g. dragging above the sticky header)
	$effect(() => {
		const handler = () => selection.handleMouseUp();
		window.addEventListener('mouseup', handler);
		return () => window.removeEventListener('mouseup', handler);
	});

	function handleSaveComment(body: string) {
		if (!selection.commentingAt) return;
		const { line, endLine } = selection.commentingAt;
		commentStore.add(file.path, line, endLine, body);
		selection.clearCommenting();
	}

	function lineTypeClass(type: DiffLine['type']): string {
		if (type === 'add') return 'bg-success/10';
		if (type === 'delete') return 'bg-error/10';
		return '';
	}

	function lineGutterClass(type: DiffLine['type']): string {
		if (type === 'add') return 'bg-success/25 text-success';
		if (type === 'delete') return 'bg-error/25 text-error';
		return 'text-base-content/40';
	}

	function linePrefix(type: DiffLine['type']): string {
		if (type === 'add') return '+';
		if (type === 'delete') return '-';
		return ' ';
	}
</script>

<div data-testid="raw-view">
	{#each file.hunks as hunk, hunkIdx (hunkIdx)}
		<div class="border-b border-base-300">
			{#if isDiffMode && hunk.header}
				<div class="bg-base-200/50 px-4 py-1 font-mono text-xs text-base-content/50">
					{hunk.header}
				</div>
			{/if}

			<table class="w-full font-mono text-sm border-collapse">
				<tbody>
					{#each hunk.lines as line, lineIdx (`${hunkIdx}-${lineIdx}`)}
						{@const flatIdx = hunkOffsets[hunkIdx] + lineIdx}
						{@const lineNo = selection.getLineNumber(line)}
						{@const lineComments = commentStore.getForLine(file.path, lineNo)}
						{@const inRange = selection.isHighlighted(lineNo)}
						{@const showCommentBox = selection.commentingAt?.anchorIndex === flatIdx}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<tr
							class="hover:bg-base-200/50 {isDiffMode ? lineTypeClass(line.type) : ''} {inRange ? 'border-l-4 border-l-info' : ''}"
							onmouseenter={() => selection.handleMouseEnter(line, flatIdx)}
						>
							{#if isDiffMode}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<td
									class="w-12 text-right px-2 select-none cursor-pointer border-r border-base-300 {inRange ? 'bg-info/20 text-info' : lineGutterClass(line.type)}"
									onmousedown={() => selection.handleMouseDown(line, flatIdx)}
									title="Click to comment, drag for range"
								>
									{line.old_no ?? ''}
								</td>
							{/if}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<td
								data-testid="line-gutter"
								class="w-12 text-right px-2 select-none cursor-pointer border-r border-base-300 {inRange ? 'bg-info/20 text-info' : lineGutterClass(line.type)}"
								onmousedown={() => selection.handleMouseDown(line, flatIdx)}
								title="Click to comment, drag for range"
							>
								{line.new_no ?? ''}
							</td>
							{#if isDiffMode}
								<td class="px-1 w-4 select-none {inRange ? 'bg-info/20 text-info' : lineGutterClass(line.type)}">
									{linePrefix(line.type)}
								</td>
							{/if}
							<td class="px-2 whitespace-pre-wrap break-all {isDiffMode && line.type === 'add' ? 'bg-success/5' : isDiffMode && line.type === 'delete' ? 'bg-error/5' : 'bg-base-100'}">
								{@html highlightLine(line.content, language)}
							</td>
						</tr>

						{#if lineComments.length > 0 || showCommentBox}
							<tr>
								<td colspan={colSpan}>
									{#each lineComments as comment (comment.id)}
										<CommentThread {comment} />
									{/each}
									{#if showCommentBox}
										<CommentBox
											onSave={handleSaveComment}
											onCancel={() => selection.clearCommenting()}
											startLine={selection.commentingAt?.line}
											endLine={selection.commentingAt?.endLine}
										/>
									{/if}
								</td>
							</tr>
						{/if}
					{/each}
				</tbody>
			</table>
		</div>
	{/each}
</div>
