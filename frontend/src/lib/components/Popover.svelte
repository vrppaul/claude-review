<script lang="ts" module>
	import { createAttachmentKey, type Attachment } from 'svelte/attachments';

	// Whatever can take the keyboard inside a pane, in the order the page has it
	const FOCUSABLE = 'input, textarea, select, button, a[href], [tabindex]:not([tabindex="-1"])';

	// How the control that opens a popover is made known to it, as part of what it is given to carry
	const HELD_AS_CONTROL = createAttachmentKey();
	// Where along the control the arrow points: its middle
	const MIDDLE = 0.5;

	/** What the control that opens a popover carries: spread on it, it says what it opens, and opens it. */
	export type TriggerProps = {
		'aria-haspopup': 'dialog';
		'aria-expanded': boolean;
		'aria-controls': string | undefined;
		onclick: () => void;
	} & Record<symbol, Attachment<HTMLElement>>;

	/** The first thing in a pane that takes the keyboard, if anything does. */
	function firstFocusable(pane: HTMLElement): HTMLElement | null {
		return pane.querySelector<HTMLElement>(FOCUSABLE);
	}
</script>

<script lang="ts">
	import { tick, type Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import PopoverPanel, { type Placement } from './PopoverPanel.svelte';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		/** Whether the pane is open: the reader's to change, by the control or by leaving the pane. */
		open: boolean;
		/** What the pane is called, said to whoever cannot see it. */
		label: string;
		placement: Placement;
		/** The control that opens it, drawn by whoever uses the popover, carrying the props it is handed. */
		trigger: Snippet<[TriggerProps]>;
		children: Snippet;
	}

	let { open = $bindable(), label, placement, trigger, children, ...marked }: Props = $props();

	const paneId = $props.id();
	let control = $state<HTMLElement>();
	let pane = $state<HTMLDivElement>();
	let around = $state<HTMLElement>();

	// How far in from the edge the pane lines up with the arrow points
	const arrowOffset = $derived(open && control ? control.offsetWidth * MIDDLE : 0);

	const triggerProps = $derived<TriggerProps>({
		'aria-haspopup': 'dialog',
		'aria-expanded': open,
		'aria-controls': open ? paneId : undefined,
		onclick: () => (open = !open),
		[HELD_AS_CONTROL]: holdControl
	});

	/** The control announces itself as it is drawn, and is let go as it goes. */
	function holdControl(element: HTMLElement): () => void {
		control = element;
		return () => (control = undefined);
	}

	// An open pane takes the keyboard, unless something in it already has — a field it opened on
	$effect(() => {
		if (pane && !pane.contains(document.activeElement)) firstFocusable(pane)?.focus();
	});

	// A pane closing with the keyboard in it hands the keyboard back to its control, not to nowhere.
	// Asked before the pane is taken off the page, while it still holds the focus.
	$effect.pre(() => {
		if (!open && pane?.contains(document.activeElement)) void tick().then(() => control?.focus());
	});

	/** Pressing anywhere outside closes the pane, and leaves the keyboard where the reader pressed. */
	function closeIfOutside(event: PointerEvent) {
		if (open && around && !around.contains(event.target as Node)) open = false;
	}

	function closeOnEscape(event: KeyboardEvent) {
		if (open && event.key === 'Escape') open = false;
	}
</script>

<svelte:document onpointerdown={closeIfOutside} />
<svelte:window onkeydown={closeOnEscape} />

<div bind:this={around} class="relative">
	{@render trigger(triggerProps)}
	{#if open}
		<PopoverPanel {...marked} bind:pane id={paneId} role="dialog" {label} {placement} {arrowOffset}>
			{@render children()}
		</PopoverPanel>
	{/if}
</div>
