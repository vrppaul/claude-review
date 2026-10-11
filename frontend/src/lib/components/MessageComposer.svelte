<script lang="ts">
	import { tick } from 'svelte';
	import type { Thread } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { threadsIn, withMention, withoutThread } from '$lib/anchors/mentions';
	import { useReview } from '$lib/review/context';
	import { messageOf } from '$lib/utils/errors';
	import AttachedImages from './AttachedImages.svelte';
	import MentionPicker from './MentionPicker.svelte';
	import { Mentions, optionIdOf, tokenOf, type Mentionable } from './mentions.svelte';

	// What the field says when a message could not be sent and nothing said why
	const SENDING_FAILED = 'Could not send';
	// What it says when it took off an image it could not show
	const IMAGE_LOST = 'An image could not be shown and was taken off the message';

	interface Props {
		/** Called as a message goes: sending is a deliberate act, and the conversation follows it to its foot. */
		onSending: () => void;
	}

	let { onSending }: Props = $props();
	const review = useReview();
	const composer = review.conversation.composer;
	const listId = $props.id();

	let field = $state<HTMLTextAreaElement | null>(null);
	let sending = $state(false);
	let failed = $state<string | null>(null);

	const mentions = new Mentions({ threads: () => review.threads.all, files: () => review.diff.files });
	// The message being written lives in the review's composer, so hiding
	// the panel or reloading the page does not lose it
	const draft = $derived(composer.text);
	// Threads this message points at, read back from the text every time: a
	// token deleted like a word takes its reference with it
	const pointed = $derived(threadsIn(draft, review.threads.all));
	// A screenshot can be the whole question, so words are not required; an
	// image still on its way is waited for
	const canSend = $derived(
		(draft.trim().length > 0 || composer.attachments.images.length > 0) &&
			!sending &&
			composer.attachments.uploading === 0
	);

	// Asked for from the keyboard, perhaps before the panel was open: taken
	// once the field is drawn
	$effect(() => {
		if (!field || !review.layout.agentPanel.inputWanted) return;
		field.focus();
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
		if (pickerKey(event)) {
			event.preventDefault();
		} else if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
			event.preventDefault();
			void send();
		}
	}

	async function onPaste(event: ClipboardEvent) {
		const refusal = await composer.attachments.takePaste(event, review.limits);
		if (refusal) failed = refusal;
	}

	/**
	 * An image that cannot be drawn: most often a review restarted under the
	 * draft, but a file the browser cannot decode looks the same from here.
	 */
	function onImageLost(imageId: string) {
		composer.attachments.forget(imageId);
		failed = IMAGE_LOST;
	}

	/** Open the picker on everything, from the button beside the field. */
	function mention() {
		mentions.openOnEverything();
		field?.focus();
	}

	async function send() {
		if (!canSend) return;
		sending = true;
		failed = null;
		onSending();
		try {
			await review.conversation.send(pointed);
			mentions.close();
		} catch (error) {
			failed = messageOf(error, SENDING_FAILED);
		} finally {
			sending = false;
		}
	}
</script>

<div class="relative">
	{#if mentions.shown}
		<MentionPicker {mentions} {listId} onTake={take} />
	{/if}

	{#if pointed.length > 0}
		<div class="mb-2 flex flex-wrap gap-1">
			{#each pointed as thread (thread.id)}
				<span data-testid="pointed-thread" class="cr-thread-chip">
					{anchorShortPlace(thread.anchor)}
					<button
						type="button"
						data-testid="drop-thread"
						class="px-1"
						aria-label="Take this thread out of the message"
						onclick={() => drop(thread)}>×</button
					>
				</span>
			{/each}
		</div>
	{/if}
	<AttachedImages attachments={composer.attachments} disabled={sending} onLost={onImageLost} />
	<textarea
		data-testid="panel-input"
		bind:this={field}
		class="cr-field cr-comment-body w-full resize-y rounded px-3 py-2"
		rows="2"
		placeholder="Ask about anything, or paste a screenshot…"
		aria-label="Message to the agent"
		aria-controls={mentions.shown ? listId : undefined}
		aria-activedescendant={mentions.shown ? optionIdOf(listId, mentions.highlighted) : undefined}
		aria-autocomplete="list"
		value={draft}
		oninput={onInput}
		onkeydown={onKeydown}
		onpaste={onPaste}
	></textarea>
	<div class="mt-2 flex items-center gap-2">
		<button type="button" data-testid="mention-thread" class="btn btn-ghost btn-xs" onclick={mention}>
			@ thread or file
		</button>
		<span class="cr-faint hidden text-xs lg:inline">Ctrl+Enter sends</span>
		<div class="flex-1"></div>
		{#if failed}
			<span data-testid="panel-error" class="text-xs text-error">{failed}</span>
		{/if}
		<button type="button" data-testid="send-message" class="btn btn-primary btn-xs" disabled={!canSend} onclick={send}>
			{sending ? 'Sending' : 'Send'}
		</button>
	</div>
</div>
