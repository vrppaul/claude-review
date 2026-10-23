<script lang="ts">
	import { untrack } from 'svelte';
	import type { CommentSeverity, WrittenAt } from '$lib/types';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { isComposingText } from '$lib/dom/keyboard';
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import Actions from '$lib/ui/Actions.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Card from '$lib/ui/Card.svelte';
	import type { CardHanging } from '$lib/ui/card';
	import CardBar from '$lib/ui/CardBar.svelte';
	import ConfirmPopover from '$lib/ui/ConfirmPopover.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import Field from '$lib/ui/Field.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Segment from '$lib/ui/Segment.svelte';
	import Segmented from '$lib/ui/Segmented.svelte';
	import Unfolding from '$lib/ui/Unfolding.svelte';
	import type { Voice } from '$lib/ui/voice';
	import { hasSuggestion, withSuggestion } from '$lib/utils/suggestion';
	import { ASK_AGENT_NOW, HANDED_WHILE_REWRITTEN } from './agent-waits';
	import AttachedImages from './AttachedImages.svelte';
	import { FIELD_KEYS, isFieldChord } from './keymap';
	import { PLACEHOLDERS } from './placeholders';

	// What is asked before words written in the field are dropped, and its two answers
	const DISCARD_QUESTION = 'Discard this comment?';
	const DISCARD = 'Discard';
	const KEEP_WRITING = 'Keep writing';
	// What the field says when it took off an image it could not show
	const IMAGE_LOST = 'An image could not be shown and was taken off the comment';
	// What a field is called where no place is said above it: inside its thread, a reply or words rewritten. A
	// comment on lines or on the story's words is named by its place, said on its card's bar
	const NAMES_IN_ITS_THREAD: Record<WrittenAt['kind'], string> = {
		new: 'Comment',
		story: 'Comment',
		reply: 'Reply',
		edit: 'Rewrite'
	};
	const SEVERITIES: { value: CommentSeverity; label: string }[] = [
		{ value: 'note', label: 'Note' },
		{ value: 'question', label: 'Question' },
		{ value: 'blocker', label: 'Blocker' }
	];
	const SUGGEST_A_CHANGE = 'Suggest a change';

	/** What the field's chord and its main button do, by what is being written: said at the start of its acts. */
	interface MainAct {
		keys: string;
		act: string;
	}

	const MAIN_ACTS: Record<WrittenAt['kind'], MainAct> = {
		new: { keys: `${FIELD_KEYS} adds`, act: 'Add to review' },
		story: { keys: `${FIELD_KEYS} adds`, act: 'Add to review' },
		reply: { keys: `${FIELD_KEYS} adds`, act: 'Add to review' },
		edit: { keys: `${FIELD_KEYS} saves`, act: 'Save' }
	};

	/**
	 * Where it is written: as the card it becomes, hanging where that will, a card of the reader's, headed by where
	 * it hangs; or inside the thread it joins or rewrites, whose card is drawn round it already, edged in the colour
	 * of whose thread it is.
	 */
	type WrittenAs =
		/** label: where the comment hangs, said at the start of its card's bar: "Line 42". */
		{ hangs: CardHanging; label: string; voice?: never } | { hangs: 'in-its-thread'; voice: Voice; label?: never };

	type Props = WrittenAs & {
		/** What is being written: held by the review, so it outlives this field. */
		field: CommentField;
		/** Put what is written into the review. */
		onSave: () => void;
		/** Hand this one over now, rather than with the rest of the review. */
		onAsk?: (() => void) | undefined;
		onCancel: () => void;
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
	// Whether it comes in as it is drawn: a field the reader opens just now, taking the cursor, comes down and fades
	// in over a fold's time; one drawn again, or brought back by a reload, stands at once. Read once, as it is drawn
	const comesIn = untrack(() => field.focusWanted);

	let failed = $state<string | null>(null);
	let textarea: HTMLTextAreaElement | undefined = $state();
	// Whether the reader is being asked if what they wrote may be dropped
	let askingToDiscard = $state(false);

	// An edit of words the agent was handed since it opened can no longer be said: it says why where its keys stand
	const handedSince = $derived(review.threads.rewritesHanded(field));
	// A screenshot can be the whole comment, so words are not required; an
	// image still on its way is waited for
	const sayable = $derived(field.sayable && !handedSince);

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

<!-- A comment being written is drawn as the card it becomes, on a dashed edge: where the card will stand, as wide,
	pointing up at what it is about, its bar saying where it hangs, the way to suggest a change and what it asks for.
	A reply is written at the foot of the card it joins, and is no card of its own -->
<Unfolding byReader={comesIn} fading testId="comment-box-coming">
	{#if hangs === 'in-its-thread'}
		<div data-testid="comment-box" class="flex flex-col gap-2">
			{@render writing()}
		</div>
	{:else}
		<Card
			tone="reader"
			{hangs}
			beingWritten
			testId="comment-box"
			data-tour={field.at.kind === 'new' ? tourStop('comment-field') : undefined}
			foot={writingInTheCard}
		>
			{#snippet bar()}
				<CardBar testId="comment-bar">
					{#snippet place()}
						<label for={fieldId}>{label}</label>
					{/snippet}
					{#if suggestFrom && suggestFrom.length > 0}
						<Button
							tone="secondary"
							size="xs"
							testId="suggest-change"
							disabled={hasSuggestion(field.text)}
							onclick={suggest}
						>
							<Icon name="suggestion" size="xs" />
							{SUGGEST_A_CHANGE}
						</Button>
					{/if}
					{#snippet end()}
						{#if severityPicker}
							{@render severities()}
						{/if}
					{/snippet}
				</CardBar>
			{/snippet}
		</Card>
	{/if}
</Unfolding>

<!-- What the comment asks for, picked: at its card's bar's end, or beside its keys where it is rewritten in its
	thread, whose bar is the thread's -->
{#snippet severities()}
	<Segmented label="What the comment asks for" size="xs" testId="severity-picker">
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
{/snippet}

<!-- At the foot of the card the comment becomes, the field and its acts one under another -->
{#snippet writingInTheCard()}
	<div class="flex flex-col gap-2">
		{@render writing()}
	</div>
{/snippet}

<!-- The field and what goes with it: its images, why it could not be added, and what can be done with it, the
	keys the field takes said at the start of its acts, or why it can no longer be said -->
{#snippet writing()}
	<Field
		bind:element={textarea}
		bind:value={field.text}
		holds="comment"
		{voice}
		testId="comment-input"
		id={fieldId}
		aria-label={label ? undefined : NAMES_IN_ITS_THREAD[field.at.kind]}
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
			{#if handedSince}
				<span data-testid="comment-unsayable" class="cr-muted text-xs">{HANDED_WHILE_REWRITTEN}</span>
			{:else}
				<span data-testid="comment-keys" class="cr-faint text-xs">{MAIN_ACTS[field.at.kind].keys}</span>
			{/if}
			{#if severityPicker && hangs === 'in-its-thread'}
				{@render severities()}
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
				<Button tone="asking" size="sm" testId="ask-now" disabled={!sayable} onclick={ask}>{ASK_AGENT_NOW}</Button>
			{/if}
		{/snippet}
		{#snippet main()}
			<Button tone="primary" size="sm" testId="save-comment" disabled={!sayable} onclick={save}>
				{MAIN_ACTS[field.at.kind].act}
			</Button>
		{/snippet}
	</Actions>
{/snippet}
