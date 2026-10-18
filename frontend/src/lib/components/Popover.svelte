<script lang="ts" module>
	import { createAttachmentKey, type Attachment } from 'svelte/attachments';

	// Whatever can take the keyboard inside a pane, in the order the page has it
	const FOCUSABLE = 'input, textarea, select, button, a[href], [tabindex]:not([tabindex="-1"])';

	// How the control that opens a popover is made known to it, as part of what it is given to carry
	const HELD_AS_CONTROL = createAttachmentKey();

	/** What the control that opens a popover carries: spread on it, it says what it opens, and opens it. */
	type TriggerProps = {
		'aria-haspopup': 'dialog';
		'aria-expanded': boolean;
		'aria-controls': string | undefined;
		onclick: () => void;
	} & Record<symbol, Attachment<HTMLElement>>;

	/** The first thing in a pane that takes the keyboard, if anything does. */
	function firstFocusable(pane: HTMLElement): HTMLElement | null {
		return pane.querySelector<HTMLElement>(FOCUSABLE);
	}

	/** What has the keyboard, if anything on the page does. */
	function focusedElement(): HTMLElement | null {
		const focused = document.activeElement;
		return focused instanceof HTMLElement && focused !== document.body ? focused : null;
	}

	/**
	 * Whether something is in a modal dialog open over the page. A modal is a
	 * layer above every pane: one opened from inside a pane — a question asked before a comment is lost —
	 * leaves the pane open under it, takes the keyboard, the presses and
	 * Escape while it is open, and gives the keyboard back into the pane as it
	 * closes.
	 */
	function inModalAbove(target: EventTarget | null): boolean {
		return target instanceof Element && target.closest('dialog[open]') !== null;
	}
</script>

<script lang="ts">
	import { tick, untrack, type Snippet } from 'svelte';
	import { isComposingText } from '$lib/dom/keyboard';
	import type { TourTarget } from '$lib/guide/tour';
	import { arrowOffsetTo, type PaneHead, type PaneWidth, type Placement } from '$lib/ui/pane';
	import PopoverPanel from '$lib/ui/PopoverPanel.svelte';

	interface Props {
		/** Whether the pane is open: the reader's to change, by the control or by leaving the pane. */
		open: boolean;
		/** What the pane is called, said to whoever cannot see it. */
		label: string;
		placement: Placement;
		width: PaneWidth;
		/** What heads it, beside the way to close it, where it is headed. */
		heading?: string | undefined;
		/** What stands beside its heading: a count, an act on all it holds. */
		aside?: Snippet | undefined;
		testId: string;
		/** The name the tour lights it by, where the tour stops at it. */
		tour?: TourTarget | undefined;
		/** A key pressed inside it, for a pane that answers one of its own. */
		onkeydown?: ((event: KeyboardEvent) => void) | undefined;
		/** The control that opens it, drawn by whoever uses the popover, carrying the props it is handed. */
		trigger: Snippet<[TriggerProps]>;
		children: Snippet;
		/** What stays at its foot while what it holds scrolls: the act it leads to. */
		foot?: Snippet | undefined;
	}

	let {
		open = $bindable(),
		label,
		placement,
		width,
		heading,
		aside,
		testId,
		tour,
		onkeydown,
		trigger,
		children,
		foot
	}: Props = $props();

	const paneId = $props.id();
	let control = $state<HTMLElement>();
	let pane = $state<HTMLDivElement>();
	let body = $state<HTMLDivElement>();
	let around = $state<HTMLElement>();
	// What had the keyboard as the pane opened — its control, or a field a key opened it from —
	// which gets it back when the pane closes with the keyboard in it
	let keyboardWasOn: HTMLElement | null = null;
	// Whether the keyboard is this popover's: it came in, and has gone to nothing else since. A
	// button disabled under it, or a press on the pane's words, sends it to no element at all,
	// which still leaves it here
	let keyboardHere = false;

	// How far in from the edge the pane lines up with the arrow points
	const arrowOffset = $derived(open ? arrowOffsetTo(control) : 0);
	// What heads the pane where it is headed: its heading, and the way to close it as Escape does
	const head = $derived<PaneHead | undefined>(heading === undefined ? undefined : { heading, close, aside });

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

	// An open pane gives the keyboard to the first of what it holds, unless something in it already has it — a
	// field it opened on. Only where it holds nothing that takes the keyboard does its close take it
	$effect(() => {
		if (pane && body && !pane.contains(document.activeElement)) (firstFocusable(body) ?? firstFocusable(pane))?.focus();
	});

	/** Close the pane from the close at its head, as Escape does: the keyboard goes back as it would then. */
	function close() {
		open = false;
	}

	// Opening, it notes what has the keyboard, before the pane is drawn and takes it; closing, it
	// hands the keyboard back, rather than leave it nowhere
	$effect.pre(() => {
		if (open) untrack(noteOpening);
		else untrack(handBack);
	});

	function noteOpening() {
		keyboardWasOn = focusedElement();
		keyboardHere = false;
	}

	/**
	 * The keyboard the pane held goes back to what had it before, or to the
	 * control if that is gone — without moving the screen: where the reader is
	 * looking is theirs, whatever they did while the pane was open. It goes
	 * back once the pane has gone, and only from where the pane's going left
	 * it: on nothing, or on the control pressed to close it. A row of the pane
	 * may have taken the reader to a thread drawn as the pane went, which
	 * keeps it.
	 */
	function handBack() {
		if (!keyboardHere) return;
		keyboardHere = false;
		void tick().then(giveBack);
	}

	/** Give the keyboard back to what had it before the pane opened, if it is where the pane's going left it. */
	function giveBack() {
		const focused = focusedElement();
		if (focused !== null && focused !== control) return;
		const back = keyboardWasOn?.isConnected ? keyboardWasOn : control;
		back?.focus({ preventScroll: true });
	}

	/** The keyboard went somewhere: to anything outside, which closes the pane; to nothing, or a modal above, which keeps it. */
	function noteKeyboardLeaving(event: FocusEvent) {
		const next = event.relatedTarget;
		if (!(next instanceof Node) || around?.contains(next) || inModalAbove(next)) return;
		keyboardHere = false;
		if (open) open = false;
	}

	/** Pressing anywhere outside closes the pane, and leaves the keyboard where the reader pressed. */
	function closeIfOutside(event: PointerEvent) {
		if (!open || !around || !(event.target instanceof Node) || around.contains(event.target)) return;
		if (inModalAbove(event.target)) return;
		keyboardHere = false;
		open = false;
	}

	function closeOnEscape(event: KeyboardEvent) {
		if (open && event.key === 'Escape' && !isComposingText(event) && !inModalAbove(event.target)) open = false;
	}
</script>

<svelte:document onpointerdown={closeIfOutside} />
<svelte:window onkeydown={closeOnEscape} />

<div bind:this={around} class="relative" onfocusin={() => (keyboardHere = true)} onfocusout={noteKeyboardLeaving}>
	{@render trigger(triggerProps)}
	{#if open}
		<!-- It takes the keyboard itself, as a native dialog does, so a press on its words keeps it in -->
		<PopoverPanel
			bind:pane
			bind:body
			id={paneId}
			role="dialog"
			tabindex={-1}
			data-tour={tour}
			{label}
			{placement}
			{width}
			arrow
			{arrowOffset}
			{head}
			{testId}
			{onkeydown}
			{foot}
		>
			{@render children()}
		</PopoverPanel>
	{/if}
</div>
