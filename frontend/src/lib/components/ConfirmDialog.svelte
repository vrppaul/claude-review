<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import Dialog from './Dialog.svelte';
	import type { Closing } from './dialog-closing';

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

<!-- A question before something written is lost: the safe answer comes first, and takes the keyboard; the
	other loses it, and is drawn as what destroys -->
<Dialog label={question} data-testid={testId} class="w-full max-w-sm" {onClose}>
	{#snippet children({ close, closeThen }: Closing)}
		<p class="mb-4 text-sm font-semibold">{question}</p>
		<div class="flex justify-end gap-2">
			<Button tone="quiet" size="sm" data-testid="confirm-keep" onclick={close}>{keep}</Button>
			<Button tone="danger" size="sm" data-testid="confirm-go-ahead" onclick={() => closeThen(onGoAhead)}>
				{goAhead}
			</Button>
		</div>
	{/snippet}
</Dialog>
