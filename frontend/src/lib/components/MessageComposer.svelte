<script lang="ts">
	import { tick } from 'svelte';
	import type { Thread } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { threadsIn, withMention, withoutThread } from '$lib/anchors/mentions';
	import { isComposingText, isTypingTarget } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import Chip from '$lib/ui/Chip.svelte';
	import Field from '$lib/ui/Field.svelte';
	import AttachedImages from './AttachedImages.svelte';
	import { FIELD_KEYS, isFieldChord } from './keymap';
	import MentionPicker from './MentionPicker.svelte';
	import { Mentions, optionIdOf, tokenOf, type Mentionable } from './mentions.svelte';

	// What the field says when it took off an image it could not show
	const IMAGE_LOST = 'An image could not be shown and was taken off the message';
	// What the cross in a thread's chip does, said to whoever cannot see it and under the pointer
	const DROP_THREAD = 'Take this thread out of the message';

	interface Props {
		/** Called as a message goes: sending is a deliberate act, and the conversation follows it to its foot. */
		onSending: () => void;
	}

	let { onSending }: Props = $props();
	const review = useReview();
	const composer = review.conversation.composer;
	const listId = $props.id();

	let field = $state<HTMLTextAreaElement>();
	// What the field says of the last thing pasted that it could not take, until a message is sent
	let noted = $state<string | null>(null);

	const mentions = new Mentions({ threads: () => review.threads.all, files: () => review.diff.files });
	// The message being written lives in the review's composer, so hiding
	// the panel or reloading the page does not lose it
	const draft = $derived(composer.text);
	// Threads this message points at, read back from the text every time: a
	// token deleted like a word takes its reference with it
	const pointed = $derived(threadsIn(draft, review.threads.all));
	// A screenshot can be the whole question, so words are not required; an
	// image still on its way is waited for, and so is a message, and so is a
	// review that cannot be reached
	const canSend = $derived(
		(draft.trim().length > 0 || composer.attachments.images.length > 0) &&
			!review.conversation.sending &&
			composer.attachments.uploading === 0 &&
			review.link.connected
	);
	// The field's own note, or why the last message did not go
	const whatWentWrong = $derived(noted ?? review.conversation.failed);

	// Asked for from the keyboard, perhaps before the panel was open: taken
	// once the field is drawn — never out of another field the reader is typing in
	$effect(() => {
		if (!field || !review.layout.agentPanel.inputWanted) return;
		if (!isTypingTarget(document.activeElement)) field.focus();
		review.layout.agentPanel.inputTaken();
	});

	function onInput(event: Event & { currentTarget: HTMLTextAreaElement }) {
		const { value, selectionStart } = event.currentTarget;
		composer.setText(value);
		mentions.follow({ text: value, caret: selectionStart });
	}

	/** Put the token where the mention was being typed, and carry on typing after it. */
	async function take(pick: Mentionable) {
		if (!field) return;
		const typed = withMention({ text: draft, caret: field.selectionStart }, tokenOf(pick));
		composer.setText(typed.text);
		mentions.close();
		field.focus();
		await tick();
		field.setSelectionRange(typed.caret, typed.caret);
	}

	/** Take a thread out of the message by taking its token out of the words. */
	function drop(thread: Thread) {
		composer.setText(withoutThread(draft, thread));
	}

	/** The keys the picker answers while it is on screen; whether this was one of them. */
	function pickerKey(event: KeyboardEvent): boolean {
		if (!mentions.shown) return false;
		if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
			mentions.step(event.key === 'ArrowDown' ? 1 : -1);
		} else if (event.key === 'Enter' && !event.shiftKey && mentions.chosen) {
			void take(mentions.chosen);
		} else if (event.key === 'Escape') {
			mentions.close();
		} else {
			return false;
		}
		return true;
	}

	function onKeydown(event: KeyboardEvent) {
		if (isComposingText(event)) return;
		if (pickerKey(event)) {
			event.preventDefault();
		} else if (isFieldChord(event)) {
			event.preventDefault();
			void send();
		}
	}

	async function onPaste(event: ClipboardEvent) {
		const refusal = await composer.attachments.takePaste(event, review.limits);
		if (refusal) noted = refusal;
	}

	/**
	 * An image that cannot be drawn: most often a review restarted under the
	 * draft, but a file the browser cannot decode looks the same from here.
	 */
	function onImageLost(imageId: string) {
		composer.attachments.forget(imageId);
		noted = IMAGE_LOST;
	}

	/** Open the picker on everything, from the button beside the field. */
	function mention() {
		mentions.openOnEverything();
		field?.focus();
	}

	async function send() {
		if (!canSend) return;
		noted = null;
		onSending();
		if (await review.conversation.send(pointed)) mentions.close();
	}
</script>

<div class="relative">
	{#if mentions.shown}
		<MentionPicker {mentions} {listId} onTake={take} />
	{/if}

	{#if pointed.length > 0}
		<div class="mb-2 flex flex-wrap gap-1">
			{#each pointed as thread (thread.id)}
				<Chip voice="reader" testId="pointed-thread" removing={DROP_THREAD} onRemove={() => drop(thread)}>
					{anchorShortPlace(thread.anchor)}
				</Chip>
			{/each}
		</div>
	{/if}
	<AttachedImages attachments={composer.attachments} disabled={review.conversation.sending} onLost={onImageLost} />
	<Field
		bind:element={field}
		holds="message"
		voice="reader"
		testId="panel-input"
		placeholder="Ask about anything, or paste a screenshot…"
		maxlength={review.limits.max_text_length}
		aria-label="Message to the agent"
		aria-controls={mentions.shown ? listId : undefined}
		aria-activedescendant={mentions.shown ? optionIdOf(listId, mentions.highlighted) : undefined}
		aria-autocomplete="list"
		value={draft}
		oninput={onInput}
		onkeydown={onKeydown}
		onpaste={onPaste}
	/>
	<div class="mt-2 flex items-center gap-2">
		<Button tone="quiet" size="xs" testId="mention-thread" onclick={mention}>@ thread or file</Button>
		<span class="cr-faint hidden text-xs lg:inline">{FIELD_KEYS} sends</span>
		<div class="flex-1"></div>
		{#if whatWentWrong}
			<span data-testid="panel-error" class="text-xs text-error">{whatWentWrong}</span>
		{/if}
		<Button tone="primary" size="xs" testId="send-message" disabled={!canSend} onclick={send}>
			{review.conversation.sending ? 'Sending' : 'Send'}
		</Button>
	</div>
</div>
