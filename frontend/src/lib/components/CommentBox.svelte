<script lang="ts">
	import type { CommentSeverity } from '$lib/types';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { useReview } from '$lib/review/context';
	import AttachedImages from './AttachedImages.svelte';

	// What opens a suggested replacement, and what closes it on a line of its own
	const SUGGESTION_FENCE = '```suggestion';
	const FENCE_CLOSE = '\n```';
	// The tallest the field grows, in pixels, before it scrolls instead
	const TALLEST = 480;
	// What the field says when it took off an image it could not show
	const IMAGE_LOST = 'An image could not be shown and was taken off the comment';
	const SEVERITIES: { value: CommentSeverity; label: string }[] = [
		{ value: 'note', label: 'Note' },
		{ value: 'question', label: 'Question' },
		{ value: 'blocker', label: 'Blocker' }
	];

	interface Props {
		/** What is being written: held by the review, so it outlives this field. */
		field: CommentField;
		onSave: (body: string, severity: CommentSeverity, images: string[]) => void;
		/** Hand this one over now, rather than with the rest of the review. */
		onAsk?: ((body: string, severity: CommentSeverity, images: string[]) => void) | undefined;
		onCancel: () => void;
		/** Where the comment hangs, said above the field: "Line 42". */
		label?: string | undefined;
		/** The lines being commented on, so a suggestion can start from them. */
		suggestFrom?: string[] | undefined;
		/** A reply has no weight of its own: the thread's belongs to the comment. */
		severityPicker?: boolean;
		/** Written inside a thread, which already draws the card around it. */
		nested?: boolean;
	}

	let { field, onSave, onAsk, onCancel, label, suggestFrom, severityPicker = true, nested = false }: Props = $props();
	const review = useReview();

	let failed = $state<string | null>(null);
	let textarea: HTMLTextAreaElement | undefined = $state();

	// A screenshot can be the whole comment, so words are not required; an
	// image still on its way is waited for
	const sayable = $derived(
		(field.text.trim().length > 0 || field.attachments.images.length > 0) && field.attachments.uploading === 0
	);

	// Grow with the text: a suggestion inserts several lines at once, and a
	// fixed box scrolls them out of sight with nothing to say so
	$effect(() => {
		void field.text;
		if (textarea) fitToText(textarea);
	});

	// The cursor goes to the field when it is opened, or asked for again — not
	// whenever it is drawn: one drawn again, a file unfolded or the page
	// reloaded, leaves the reader where they are. A field opened near the
	// bottom of the window is brought up, so its buttons are in sight too.
	$effect(() => {
		if (!textarea || !field.focusWanted) return;
		textarea.focus();
		textarea.scrollIntoView({ block: 'nearest' });
		field.focusTaken();
	});

	function fitToText(element: HTMLTextAreaElement) {
		element.style.height = 'auto';
		element.style.height = `${Math.min(element.scrollHeight, TALLEST)}px`;
	}

	function save() {
		if (!sayable) return;
		onSave(field.text.trim(), field.severity, [...field.attachments.images]);
	}

	/**
	 * Send this one straight to whoever is answering.
	 *
	 * It is a question by definition — asking and then leaving the comment
	 * marked as a note would say two different things about the same words.
	 */
	function ask() {
		if (!sayable || !onAsk) return;
		onAsk(field.text.trim(), 'question', [...field.attachments.images]);
	}

	async function onPaste(event: ClipboardEvent) {
		failed = null;
		const refusal = await field.attachments.takePaste(event, review.limits);
		if (refusal) failed = refusal;
	}

	/** An image that cannot be drawn, taken off with a note rather than left broken. */
	function onImageLost(imageId: string) {
		field.attachments.forget(imageId);
		failed = IMAGE_LOST;
	}

	/**
	 * Start a replacement for the commented lines.
	 *
	 * Saying what the code should be instead beats describing it: the agent
	 * gets something it can apply rather than something it has to interpret.
	 */
	function suggest() {
		if (!suggestFrom || field.text.includes(SUGGESTION_FENCE)) return;
		const block = `${SUGGESTION_FENCE}\n${suggestFrom.join('\n')}${FENCE_CLOSE}`;
		const written = field.text.trim();
		field.text = written ? `${written}\n\n${block}` : block;
		requestAnimationFrame(() => selectSuggestion());
	}

	/** Put the cursor in the suggested lines, rather than after the block. */
	function selectSuggestion() {
		if (!textarea) return;
		textarea.focus();
		const from = field.text.indexOf(SUGGESTION_FENCE) + SUGGESTION_FENCE.length + 1;
		textarea.setSelectionRange(from, field.text.length - FENCE_CLOSE.length);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
			event.preventDefault();
			save();
		}
		if (event.key === 'Escape') {
			onCancel();
		}
	}
</script>

<div
	class={nested ? 'space-y-2' : 'cr-comment cr-composing space-y-3 rounded-r px-4 py-3'}
	data-tour={field.at.kind === 'new' ? 'comment-field' : undefined}
>
	<div class="flex items-center gap-3">
		{#if label}
			<span class="cr-comment-ref font-mono text-xs">{label}</span>
		{/if}
		<div class="flex-1"></div>
		{#if severityPicker}
			<div data-testid="severity-picker" class="cr-segmented">
				{#each SEVERITIES as choice (choice.value)}
					<button
						data-testid="severity-{choice.value}"
						class="cr-segment"
						aria-pressed={field.severity === choice.value}
						onclick={() => (field.severity = choice.value)}
					>
						{choice.label}
					</button>
				{/each}
			</div>
		{/if}
	</div>
	<textarea
		bind:this={textarea}
		data-testid="comment-input"
		class="cr-field cr-comment-body textarea min-h-20 w-full focus:outline-none"
		placeholder="What should change here?"
		bind:value={field.text}
		onkeydown={handleKeydown}
		onpaste={onPaste}
	></textarea>
	<AttachedImages attachments={field.attachments} onLost={onImageLost} />
	{#if failed}
		<p data-testid="comment-error" class="text-xs text-error">{failed}</p>
	{/if}
	<div class="flex items-center gap-2">
		{#if suggestFrom && suggestFrom.length > 0}
			<button
				class="btn btn-ghost btn-xs"
				data-testid="suggest-change"
				disabled={field.text.includes(SUGGESTION_FENCE)}
				onclick={suggest}
			>
				Suggest a change
			</button>
		{/if}
		<div class="flex-1"></div>
		<button class="btn btn-ghost btn-xs" data-testid="cancel-comment" onclick={onCancel}> Cancel </button>
		{#if onAsk}
			<button class="btn btn-outline btn-xs" data-testid="ask-now" disabled={!sayable} onclick={ask}> Ask now </button>
		{/if}
		<button class="btn btn-primary btn-xs" data-testid="save-comment" disabled={!sayable} onclick={save}>
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
