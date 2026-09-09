<script lang="ts">
	import { onMount } from 'svelte';
	import type { CommentSeverity, LineSide } from '$lib/types';
	import { lineRangeLabel } from '$lib/utils/line-label';

	const SUGGESTION_FENCE = '```suggestion';

	interface Props {
		onSave: (body: string, severity: CommentSeverity) => void;
		onCancel: () => void;
		side?: LineSide;
		startLine?: number;
		endLine?: number;
		initialBody?: string;
		initialSeverity?: CommentSeverity;
		/** The lines being commented on, so a suggestion can start from them. */
		suggestFrom?: string[];
	}

	let {
		onSave,
		onCancel,
		side,
		startLine,
		endLine,
		initialBody = '',
		initialSeverity = 'note',
		suggestFrom
	}: Props = $props();

	const severities: { value: CommentSeverity; label: string }[] = [
		{ value: 'note', label: 'Note' },
		{ value: 'question', label: 'Question' },
		{ value: 'blocker', label: 'Blocker' }
	];

	const label = $derived(
		startLine == null ? null : lineRangeLabel(side ?? 'new', startLine, endLine ?? startLine)
	);

	// svelte-ignore state_referenced_locally — intentional one-shot capture; component is always recreated
	let body = $state(initialBody);
	// svelte-ignore state_referenced_locally — same
	let severity = $state<CommentSeverity>(initialSeverity);

	let textareaEl: HTMLTextAreaElement;

	/** Grow with the text: a suggestion inserts several lines at once, and a
	 * fixed box scrolls them out of sight with nothing to say so. */
	function fitToText() {
		if (!textareaEl) return;
		textareaEl.style.height = 'auto';
		textareaEl.style.height = `${Math.min(textareaEl.scrollHeight, 480)}px`;
	}

	$effect(() => {
		void body;
		fitToText();
	});

	onMount(() => {
		textareaEl?.focus();
		// Commenting on a line near the bottom of the window opened the composer
		// mostly below it: focused, but with its buttons out of sight.
		textareaEl?.scrollIntoView({ block: 'nearest' });
	});

	function save() {
		if (body.trim()) onSave(body.trim(), severity);
	}

	/**
	 * Start a replacement for the commented lines.
	 *
	 * Saying what the code should be instead beats describing it: Claude gets
	 * something it can apply rather than something it has to interpret.
	 */
	function suggest() {
		if (!suggestFrom || body.includes(SUGGESTION_FENCE)) return;
		const block = `${SUGGESTION_FENCE}\n${suggestFrom.join('\n')}\n\`\`\``;
		body = body.trim() ? `${body.trim()}\n\n${block}` : block;
		requestAnimationFrame(() => {
			textareaEl?.focus();
			// Land in the block itself rather than after it
			const at = body.indexOf(SUGGESTION_FENCE) + SUGGESTION_FENCE.length + 1;
			textareaEl?.setSelectionRange(at, body.length - 4);
		});
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
	<div class="flex items-center gap-3">
		{#if label}
			<span class="cr-comment-ref font-mono text-xs">{label}</span>
		{/if}
		<div class="flex-1"></div>
		<div data-testid="severity-picker" class="cr-segmented">
			{#each severities as choice (choice.value)}
				<button
					data-testid="severity-{choice.value}"
					class="cr-segment"
					aria-pressed={severity === choice.value}
					onclick={() => (severity = choice.value)}
				>
					{choice.label}
				</button>
			{/each}
		</div>
	</div>
	<textarea
		bind:this={textareaEl}
		data-testid="comment-input"
		class="cr-comment-body textarea min-h-20 w-full bg-base-100 focus:outline-none"
		placeholder="What should change here?"
		bind:value={body}
		onkeydown={handleKeydown}
	></textarea>
	<div class="flex items-center gap-2">
		{#if suggestFrom && suggestFrom.length > 0}
			<button
				class="btn btn-ghost btn-xs"
				data-testid="suggest-change"
				disabled={body.includes(SUGGESTION_FENCE)}
				onclick={suggest}
			>
				Suggest a change
			</button>
		{/if}
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
