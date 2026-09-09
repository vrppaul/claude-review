<script lang="ts">
	import { onMount } from 'svelte';
	import type { LineSide } from '$lib/types';
	import { lineRangeLabel } from '$lib/utils/line-label';

	interface Props {
		onSave: (body: string) => void;
		onCancel: () => void;
		side?: LineSide;
		startLine?: number;
		endLine?: number;
		initialBody?: string;
	}

	let { onSave, onCancel, side, startLine, endLine, initialBody = '' }: Props = $props();

	const label = $derived(
		startLine == null ? null : lineRangeLabel(side ?? 'new', startLine, endLine ?? startLine)
	);

	// svelte-ignore state_referenced_locally — intentional one-shot capture; component is always recreated
	let body = $state(initialBody);

	let textareaEl: HTMLTextAreaElement;

	onMount(() => {
		textareaEl?.focus();
		// Commenting on a line near the bottom of the window opened the composer
		// mostly below it: focused, but with its buttons out of sight.
		textareaEl?.scrollIntoView({ block: 'nearest' });
	});

	function save() {
		if (body.trim()) onSave(body.trim());
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
			e.preventDefault();
			save();
		}
		if (e.key === 'Escape') {
			onCancel();
		}
	}
</script>

<div class="cr-comment space-y-3 rounded-r px-4 py-3">
	{#if label}
		<div class="cr-comment-ref font-mono text-xs">{label}</div>
	{/if}
	<textarea
		bind:this={textareaEl}
		data-testid="comment-input"
		class="cr-comment-body textarea min-h-20 w-full bg-base-100 focus:outline-none"
		placeholder="What should change here?"
		bind:value={body}
		onkeydown={handleKeydown}
	></textarea>
	<div class="flex items-center gap-2">
		<span class="cr-muted text-xs">Ctrl+Enter to save</span>
		<div class="flex-1"></div>
		<button class="btn btn-ghost btn-xs" data-testid="cancel-comment" onclick={onCancel}>
			Cancel
		</button>
		<button
			class="btn btn-primary btn-xs"
			data-testid="save-comment"
			disabled={!body.trim()}
			onclick={save}
		>
			Save
		</button>
	</div>
</div>
