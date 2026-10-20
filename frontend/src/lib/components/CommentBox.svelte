<script lang="ts">
	import type { CommentSeverity } from '$lib/types';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { isComposingText } from '$lib/dom/keyboard';
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import Actions from '$lib/ui/Actions.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Card from '$lib/ui/Card.svelte';
	import type { CardHanging } from '$lib/ui/card';
	import ConfirmPopover from '$lib/ui/ConfirmPopover.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import Field from '$lib/ui/Field.svelte';
	import Segment from '$lib/ui/Segment.svelte';
	import Segmented from '$lib/ui/Segmented.svelte';
	import type { Voice } from '$lib/ui/voice';
	import { hasSuggestion, withSuggestion } from '$lib/utils/suggestion';
	import AttachedImages from './AttachedImages.svelte';
	import { FIELD_KEYS, isFieldChord } from './keymap';
	import { PLACEHOLDERS } from './placeholders';

	// What is asked before words written in the field are dropped, and its two answers
	const DISCARD_QUESTION = 'Discard this comment?';
	const DISCARD = 'Discard';
	const KEEP_WRITING = 'Keep writing';
	// What the field says when it took off an image it could not show
	const IMAGE_LOST = 'An image could not be shown and was taken off the comment';
	// What a field with no place said above it is called: a reply, inside the thread it answers
	const REPLY = 'Reply';
	const SEVERITIES: { value: CommentSeverity; label: string }[] = [
		{ value: 'note', label: 'Note' },
		{ value: 'question', label: 'Question' },
		{ value: 'blocker', label: 'Blocker' }
	];

	/**
	 * Where it is written: as the card it becomes, hanging where that will, a card of the reader's; or as a reply,
	 * inside the thread it joins, whose card is drawn round it already, edged in the colour of whose thread it is.
	 */
	type WrittenAs = { hangs: CardHanging; voice?: never } | { hangs: 'in-its-thread'; voice: Voice };

	type Props = WrittenAs & {
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
	};

	let {
		field,
		onSave,
		onAsk,
		onCancel,
		label,
		suggestFrom,
		severityPicker = true,
		hangs,
		voice = 'reader'
	}: Props = $props();
	const review = useReview();
	const fieldId = $props.id();

	let failed = $state<string | null>(null);
	let textarea: HTMLTextAreaElement | undefined = $state();
	// Whether the reader is being asked if what they wrote may be dropped
	let askingToDiscard = $state(false);

	// A screenshot can be the whole comment, so words are not required; an
	// image still on its way is waited for
	const sayable = $derived(field.sayable);

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
			// Answered here, the same key is not the question's to close itself with as it opens
			event.preventDefault();
			putAway();
		}
	}
</script>

<!-- A comment being written is drawn as the card it becomes: where the card will stand, as wide, pointing up
	at what it is about. A reply is written inside the card it joins, and is no card of its own -->
{#if hangs === 'in-its-thread'}
	<div data-testid="comment-box" class="space-y-2">
		{@render writing()}
	</div>
{:else}
	<Card
		tone="reader"
		{hangs}
		testId="comment-box"
		data-tour={field.at.kind === 'new' ? tourStop('comment-field') : undefined}
	>
		<div class="cr-thread-rows">
			{@render writing()}
		</div>
	</Card>
{/if}

<!-- The field and what goes with it: where it hangs, what it asks for, its images, and what can be done with it -->
{#snippet writing()}
	<div class="flex items-center gap-3">
		{#if label}
			<label for={fieldId} class="cr-comment-ref font-mono text-xs">{label}</label>
		{/if}
		<div class="flex-1"></div>
		{#if severityPicker}
			<Segmented label="What the comment asks for" testId="severity-picker">
				{#each SEVERITIES as choice (choice.value)}
					<Segment
						testId="severity-{choice.value}"
						pressed={field.severity === choice.value}
						onclick={() => (field.severity = choice.value)}
					>
						{choice.label}
					</Segment>
				{/each}
			</Segmented>
		{/if}
	</div>
	<Field
		bind:element={textarea}
		bind:value={field.text}
		holds="comment"
		{voice}
		testId="comment-input"
		id={fieldId}
		aria-label={label ? undefined : REPLY}
		placeholder={PLACEHOLDERS[field.at.kind]}
		maxlength={review.limits.max_text_length}
		onkeydown={handleKeydown}
		onpaste={onPaste}
	/>
	<AttachedImages attachments={field.attachments} onLost={onImageLost} />
	{#if failed}
		<Failure stands="apart" testId="comment-error" said={failed} />
	{/if}
	<Actions testId="comment-actions">
		{#snippet aside()}
			{#if suggestFrom && suggestFrom.length > 0}
				<Button tone="quiet" size="sm" testId="suggest-change" disabled={hasSuggestion(field.text)} onclick={suggest}>
					Suggest a change
				</Button>
			{/if}
		{/snippet}
		{#snippet others()}
			<!-- Asked over Cancel, which asks it, or as Escape does in the field: over the words it would lose, inside
				the card, so nothing past the card's foot can cut it off -->
			<ConfirmPopover
				bind:open={askingToDiscard}
				question={DISCARD_QUESTION}
				goAhead={DISCARD}
				keep={KEEP_WRITING}
				placement="above-end"
				testId="discard-dialog"
				onGoAhead={onCancel}
			>
				{#snippet trigger(control)}
					<Button {...control} tone="quiet" size="sm" testId="cancel-comment" onclick={putAway}>Cancel</Button>
				{/snippet}
			</ConfirmPopover>
			{#if onAsk}
				<Button tone="asking" size="sm" testId="ask-now" disabled={!sayable} onclick={ask}>Ask now</Button>
			{/if}
		{/snippet}
		<Button tone="primary" size="sm" testId="save-comment" disabled={!sayable} onclick={save}>Add to review</Button>
	</Actions>
	<p class="cr-faint text-xs">
		{#if onAsk}
			{FIELD_KEYS} adds it to the review. Ask now sends this one straight away.
		{:else}
			{FIELD_KEYS} to save.
		{/if}
	</p>
{/snippet}
