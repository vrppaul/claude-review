<script lang="ts">
	interface Props {
		onSave: (body: string) => void;
		onCancel: () => void;
		startLine?: number;
		endLine?: number;
		initialBody?: string;
	}

	let { onSave, onCancel, startLine, endLine, initialBody = '' }: Props = $props();

	function lineLabel(): string | null {
		if (startLine == null) return null;
		if (endLine != null && endLine !== startLine) return `Lines ${startLine}-${endLine}`;
		return `Line ${startLine}`;
	}
	let body = $state(initialBody);

	let textareaEl: HTMLTextAreaElement;

	$effect(() => {
		textareaEl?.focus();
	});

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
			e.preventDefault();
			if (body.trim()) {
				onSave(body.trim());
			}
		}
		if (e.key === 'Escape') {
			onCancel();
		}
	}
</script>

<div class="bg-base-200 border border-base-300 rounded-lg p-4 space-y-3">
	{#if lineLabel()}
		<div class="text-xs text-info font-mono">{lineLabel()}</div>
	{/if}
	<textarea
		bind:this={textareaEl}
		class="textarea textarea-bordered w-full text-sm min-h-16 focus:outline-none focus:border-info"
		placeholder="Add your comment... (Ctrl+Enter to save, Esc to cancel)"
		bind:value={body}
		onkeydown={handleKeydown}
	></textarea>
	<div class="flex justify-end gap-2">
		<button class="btn btn-ghost btn-xs" onclick={onCancel}>Cancel</button>
		<button
			class="btn btn-primary btn-xs"
			disabled={!body.trim()}
			onclick={() => onSave(body.trim())}
		>
			Comment
		</button>
	</div>
</div>
