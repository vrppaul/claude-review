<script lang="ts">
	import Dialog from './Dialog.svelte';

	interface Props {
		/** What is asked, as the dialog says it and is named by: "Discard this comment?" */
		question: string;
		/** What the button that goes ahead says: "Discard". */
		goAhead: string;
		/** What the button that leaves things as they are says: "Keep writing". */
		keep: string;
		/** What going ahead does, once the dialog has closed and given the keyboard back. */
		onGoAhead: () => void;
		/** Called once it closes, either way, for whoever drew it to stop drawing it. */
		onClose: () => void;
		testId: string;
	}

	let { question, goAhead, keep, onGoAhead, onClose, testId }: Props = $props();
</script>

<!-- A question before something written is lost: the safe answer comes first, and takes the keyboard -->
<Dialog label={question} data-testid={testId} class="w-full max-w-sm" {onClose}>
	{#snippet children(close: () => void, closeThen: (then: () => void) => void)}
		<p class="mb-4 text-sm font-semibold">{question}</p>
		<div class="flex justify-end gap-2">
			<button type="button" data-testid="confirm-keep" class="btn btn-ghost btn-sm" onclick={close}>{keep}</button>
			<button
				type="button"
				data-testid="confirm-go-ahead"
				class="btn btn-outline btn-sm"
				onclick={() => closeThen(onGoAhead)}
			>
				{goAhead}
			</button>
		</div>
	{/snippet}
</Dialog>
