<script lang="ts">
	import type { CommentSeverity, WrittenAt } from '$lib/types';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { isComposingText } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import { hasSuggestion, withSuggestion } from '$lib/utils/suggestion';
	import AttachedImages from './AttachedImages.svelte';
	import ConfirmDialog from './ConfirmDialog.svelte';
	import { FIELD_KEYS, isFieldChord } from './keymap';

	// What is asked before words written in the field are dropped, and its two answers
	const DISCARD_QUESTION = 'Discard this comment?';
	const DISCARD = 'Discard';
	const KEEP_WRITING = 'Keep writing';
	// What the field says when it took off an image it could not show
	const IMAGE_LOST = 'An image could not be shown and was taken off the comment';
	// What a field with no place said above it is called: a reply, inside the thread it answers
	const REPLY = 'Reply';
	// What an empty field says, by what is being written in it: a reply reads as the thread's own "Write a reply…"
	const PLACEHOLDERS: Record<WrittenAt['kind'], string> = {
		new: 'What should change here?',
		story: 'What should change here?',
		edit: 'What should change here?',
		reply: 'Write a reply…'
	};
	const SEVERITIES: { value: CommentSeverity; label: string }[] = [
		{ value: 'note', label: 'Note' },
		{ value: 'question', label: 'Question' },
		{ value: 'blocker', label: 'Blocker' }
	];

	interface Props {
		/** What is being written: held by the review, so it outlives this field. */
		field: CommentField;
		/** Put what is written into the review. */
		onSave: () => void;
		/** Hand this one over now, rather than with the rest of the review. */
		onAsk?: (() => void) | undefined;
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
	const fieldId = $props.id();

	let failed = $state<string | null>(null);
	let textarea: HTMLTextAreaElement | undefined = $state();
	// Whether the reader is being asked if what they wrote may be dropped
	let askingToDiscard = $state(false);

	// A screenshot can be the whole comment, so words are not required; an
	// image still on its way is waited for
	const sayable = $derived(field.sayable);

	// Grow with the text: a suggestion inserts several lines at once, and a
	// fixed box scrolls them out of sight with nothing to say so. How tall it
	// may grow is the stylesheet's (cr-field-grows)
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

	/** As tall as the text in it: measured from nothing, as only the field itself can say. */
	function fitToText(element: HTMLTextAreaElement) {
		element.style.height = 'auto';
		element.style.height = `${element.scrollHeight}px`;
	}

	function save() {
		if (sayable) onSave();
	}

	/** Send this one straight to whoever is answering. */
	function ask() {
		if (sayable && onAsk) onAsk();
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
		if (!suggestFrom || hasSuggestion(field.text)) return;
		const { text, start, end } = withSuggestion(field.text, suggestFrom);
		field.text = text;
		requestAnimationFrame(() => selectSuggested(start, end));
	}

	/** Put the cursor over the suggested lines, rather than after the block. */
	function selectSuggested(start: number, end: number) {
		if (!textarea) return;
		textarea.focus();
		textarea.setSelectionRange(start, end);
	}

	/** Put the field away: at once when nothing in it would be lost, and only on the reader's word when something would. */
	function putAway() {
		if (field.holdsWork) askingToDiscard = true;
		else onCancel();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (isComposingText(event)) return;
		if (isFieldChord(event)) {
			event.preventDefault();
			save();
		}
		if (event.key === 'Escape') {
			// Left to the browser, the same key would close the question it opens
			event.preventDefault();
			putAway();
		}
	}
</script>

<div
	data-testid="comment-box"
	class={nested ? 'space-y-2' : 'cr-comment cr-composing space-y-3 rounded-r px-4 py-3'}
	data-tour={field.at.kind === 'new' ? 'comment-field' : undefined}
>
	<div class="flex items-center gap-3">
		{#if label}
			<label for={fieldId} class="cr-comment-ref font-mono text-xs">{label}</label>
		{/if}
		<div class="flex-1"></div>
		{#if severityPicker}
			<div data-testid="severity-picker" class="cr-segmented">
				{#each SEVERITIES as choice (choice.value)}
					<button
						type="button"
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
		id={fieldId}
		data-testid="comment-input"
		aria-label={label ? undefined : REPLY}
		class="cr-field cr-field-grows cr-comment-body textarea min-h-20 w-full"
		placeholder={PLACEHOLDERS[field.at.kind]}
		maxlength={review.limits.max_text_length}
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
				type="button"
				class="btn btn-ghost btn-xs"
				data-testid="suggest-change"
				disabled={hasSuggestion(field.text)}
				onclick={suggest}
			>
				Suggest a change
			</button>
		{/if}
		<div class="flex-1"></div>
		<button type="button" class="btn btn-ghost btn-xs" data-testid="cancel-comment" onclick={putAway}> Cancel </button>
		{#if onAsk}
			<button type="button" class="btn btn-outline btn-xs" data-testid="ask-now" disabled={!sayable} onclick={ask}>
				Ask now
			</button>
		{/if}
		<button type="button" class="btn btn-primary btn-xs" data-testid="save-comment" disabled={!sayable} onclick={save}>
			Add to review
		</button>
	</div>
	<p class="cr-faint text-xs">
		{#if onAsk}
			{FIELD_KEYS} adds it to the review. Ask now sends this one straight away.
		{:else}
			{FIELD_KEYS} to save.
		{/if}
	</p>
</div>
{#if askingToDiscard}
	<ConfirmDialog
		question={DISCARD_QUESTION}
		goAhead={DISCARD}
		keep={KEEP_WRITING}
		testId="discard-dialog"
		onGoAhead={onCancel}
		onClose={() => (askingToDiscard = false)}
	/>
{/if}
