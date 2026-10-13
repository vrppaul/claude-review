<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLDialogAttributes } from 'svelte/elements';

	interface Props extends Omit<HTMLDialogAttributes, 'children'> {
		/** What the dialog is called, said to whoever cannot see it. */
		label: string;
		/** Called once it closes, by Escape, a press outside it or its own words, for whoever drew it to stop drawing it. */
		onClose: () => void;
		/** What it holds, handed the way to close it as Escape does, so the browser gives the keyboard back. */
		children: Snippet<[close: () => void]>;
	}

	let { label, onClose, children, class: sized, ...marked }: Props = $props();

	let dialog = $state<HTMLDialogElement>();
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
</script>

<!-- A modal, drawn as the browser's own `<dialog>` and shown with `showModal()`: a layer above the page,
	which holds the keyboard inside it, and gives it back to what had it when it is closed with `close()`.
	A pane open under it neither closes nor takes what is pressed in it: `Popover` asks whether a modal
	is above it -->
<dialog
	{...marked}
	bind:this={dialog}
	aria-label={label}
	class={['cr-dialog', sized]}
	onclose={onClose}
	onpointerdown={notePress}
	onclick={closeOnBackdrop}
>
	<div class="cr-dialog-body">
		{@render children(close)}
	</div>
</dialog>
