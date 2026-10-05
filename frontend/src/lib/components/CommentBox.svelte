<script lang="ts">
	import { onMount } from 'svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import type { CommentSeverity, LineSide } from '$lib/types';
	import { ImageAttachments } from '$lib/utils/image-attachments.svelte';
	import { lineRangeLabel } from '$lib/utils/line-label';
	import AttachedImages from './AttachedImages.svelte';

	const SUGGESTION_FENCE = '```suggestion';

	interface Props {
		onSave: (body: string, severity: CommentSeverity, images: string[]) => void;
		/** Hand this one over now, rather than with the rest of the review. */
		onAsk?: (body: string, severity: CommentSeverity, images: string[]) => void;
		onCancel: () => void;
		side?: LineSide;
		startLine?: number;
		endLine?: number;
		initialBody?: string;
		initialSeverity?: CommentSeverity;
		/** Images already on the comment being edited. */
		initialImages?: string[];
		/** The lines being commented on, so a suggestion can start from them. */
		suggestFrom?: string[];
		/** A reply has no weight of its own: the thread's belongs to the comment. */
		severityPicker?: boolean;
		/** Written inside a thread, which already draws the card around it. */
		nested?: boolean;
	}

	let {
		onSave,
		onAsk,
		onCancel,
		side,
		startLine,
		endLine,
		initialBody = '',
		initialSeverity = 'note',
		initialImages = [],
		suggestFrom,
		severityPicker = true,
		nested = false
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
	// svelte-ignore state_referenced_locally — same
	const attachments = new ImageAttachments([...initialImages]);
	let failed = $state<string | null>(null);
	// Whether what was written went somewhere. A field closed any other way —
	// Cancel, a click on another line, a folded thread, another file — lets
	// the server drop what was pasted into it.
	let handedOver = false;

	$effect(() => () => {
		if (!handedOver) attachments.abandon();
	});

	// A screenshot can be the whole comment, so words are not required; an
	// image still on its way is waited for
	const sayable = $derived(
		(body.trim().length > 0 || attachments.images.length > 0) && attachments.uploading === 0
	);

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
		if (!sayable) return;
		handedOver = true;
		onSave(body.trim(), severity, $state.snapshot(attachments.images));
	}

	async function onPaste(event: ClipboardEvent) {
		failed = null;
		const refusal = await attachments.takePaste(event, diffStore.imageLimits);
		if (refusal) failed = refusal;
	}

	/** An image that cannot be drawn, taken off with a note rather than left broken. */
	function onImageLost(imageId: string) {
		attachments.forget(imageId);
		failed = 'An image could not be shown and was taken off the comment';
	}

	/**
	 * Send this one straight to whoever is answering.
	 *
	 * It is a question by definition — asking and then leaving the comment
	 * marked as a note would say two different things about the same words.
	 */
	function ask() {
		if (!sayable || !onAsk) return;
		handedOver = true;
		onAsk(body.trim(), 'question', $state.snapshot(attachments.images));
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

<div class={nested ? 'space-y-2' : 'cr-comment cr-composing space-y-3 rounded-r px-4 py-3'}>
	<div class="flex items-center gap-3">
		{#if label}
			<span class="cr-comment-ref font-mono text-xs">{label}</span>
		{/if}
		<div class="flex-1"></div>
		{#if severityPicker}
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
		{/if}
	</div>
	<textarea
		bind:this={textareaEl}
		data-testid="comment-input"
		class="cr-field cr-comment-body textarea min-h-20 w-full focus:outline-none"
		placeholder="What should change here?"
		bind:value={body}
		onkeydown={handleKeydown}
		onpaste={onPaste}
	></textarea>
	<AttachedImages {attachments} onLost={onImageLost} />
	{#if failed}
		<p data-testid="comment-error" class="text-xs text-error">{failed}</p>
	{/if}
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
		<div class="flex-1"></div>
		<button class="btn btn-ghost btn-xs" data-testid="cancel-comment" onclick={onCancel}>
			Cancel
		</button>
		{#if onAsk}
			<button class="btn btn-outline btn-xs" data-testid="ask-now" disabled={!sayable} onclick={ask}>
				Ask now
			</button>
		{/if}
		<button
			class="btn btn-primary btn-xs"
			data-testid="save-comment"
			disabled={!sayable}
			onclick={save}
		>
			Add to review
		</button>
	</div>
	<p class="cr-faint text-xs">
		{#if onAsk}
			Ctrl+Enter adds it to the review. Ask now sends this one straight away.
		{:else}
			Ctrl+Enter to save.
		{/if}
	</p>
</div>
