<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { Closing } from './dialog-closing';
	import { PANE_WIDTHS, type PaneWidth } from './pane';
	import PaneHead from './PaneHead.svelte';

	interface Props {
		/** What the dialog is called, said to whoever cannot see it. */
		label: string;
		width: PaneWidth;
		/** What heads it, beside the way to close it: none for a question, whose answers are its ways out. */
		heading?: string | undefined;
		testId: string;
		/** Called once it closes, by Escape, a press outside it or its own words, for whoever drew it to stop drawing it. */
		onClose: () => void;
		/** What it holds, handed the ways to close it. */
		children: Snippet<[closing: Closing]>;
	}

	let { label, width, heading, testId, onClose, children }: Props = $props();

	let dialog = $state<HTMLDialogElement>();
	// What the dialog's own words asked to be done once it has closed: nothing, where it is closed any other way
	let doneOnceClosed: (() => void) | null = null;
	// Whether the press now under way began on the backdrop: a selection dragged out of the
	// dialog is let go there too, and must not close it
	let pressedOnBackdrop = false;

	// A real modal from the moment it is drawn: the keyboard is held inside it,
	// and the page under it takes no keys or presses until it closes
	$effect(() => {
		if (dialog && !dialog.open) dialog.showModal();
	});

	/** A press on the backdrop lands on the dialog itself, outside what it holds. */
	function notePress(event: PointerEvent) {
		pressedOnBackdrop = event.target === dialog;
	}

	/** A press begun and let go on the backdrop closes the dialog. */
	function closeOnBackdrop(event: MouseEvent) {
		if (pressedOnBackdrop && event.target === dialog) dialog.close();
	}

	/** Close it from what it holds: never by no longer drawing it, which would leave the keyboard nowhere. */
	function close() {
		dialog?.close();
	}

	/**
	 * Close it, and then do what its words asked for. The dialog closes
	 * first, so the browser gives the keyboard back to where it was, and
	 * what was asked follows.
	 */
	function closeThen(then: () => void) {
		doneOnceClosed = then;
		close();
	}

	/** It has closed: whoever drew it is told, and then what its words asked for is done, once. */
	function closed() {
		const asked = doneOnceClosed;
		doneOnceClosed = null;
		onClose();
		asked?.();
	}
</script>

<!-- A modal, drawn as the browser's own `<dialog>` and shown with `showModal()`, in the look of every pane: a
	layer above the page, which holds the keyboard inside it, and gives it back to what had it when it is closed
	with `close()`. It is for what stands over the whole review, not by one control: a pane opened from a control
	is a `Popover` -->
<dialog
	bind:this={dialog}
	aria-label={label}
	data-testid={testId}
	class={['cr-ui-pane cr-ui-dialog', PANE_WIDTHS[width]]}
	onclose={closed}
	onpointerdown={notePress}
	onclick={closeOnBackdrop}
>
	{#if heading !== undefined}
		<PaneHead head={{ heading, close }} {testId} />
	{/if}
	<!-- What it holds, inside its edge: a press here is not a press outside it -->
	<div class="cr-scroller cr-ui-pane-body">
		{@render children({ close, closeThen })}
	</div>
</dialog>
