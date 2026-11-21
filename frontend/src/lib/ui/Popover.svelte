<script lang="ts" module>
	import { createAttachmentKey } from 'svelte/attachments';

	// Whatever can take the keyboard inside a pane, in the order the page has it
	const FOCUSABLE = 'input, textarea, select, button, a[href], [tabindex]:not([tabindex="-1"])';

	// How the control that opens a popover is made known to it, as part of what it is given to carry
	const HELD_AS_CONTROL = createAttachmentKey();

	/** The first thing in a pane that takes the keyboard, if anything does. */
	function firstFocusable(pane: HTMLElement): HTMLElement | null {
		return pane.querySelector<HTMLElement>(FOCUSABLE);
	}

	/**
	 * Whether a key leaves a pane by Tab at one of its ends: Shift+Tab from the pane itself or the first of what
	 * takes the keyboard in it, Tab from the last.
	 */
	function leavesAtAnEnd(pane: HTMLElement, event: KeyboardEvent): boolean {
		if (event.key !== 'Tab') return false;
		const stops = [pane, ...pane.querySelectorAll<HTMLElement>(FOCUSABLE)];
		const focused = document.activeElement;
		return event.shiftKey ? focused === pane || focused === stops[1] : focused === stops.at(-1);
	}

	/** What has the keyboard, if anything on the page does. */
	function focusedElement(): HTMLElement | null {
		const focused = document.activeElement;
		return focused instanceof HTMLElement && focused !== document.body ? focused : null;
	}
</script>

<script lang="ts">
	import { tick, untrack, type Snippet } from 'svelte';
	import { EveryFrame } from '$lib/dom/every-frame';
	import { isComposingText } from '$lib/dom/keyboard';
	import { type AreaBox, boxInArea, sameBox } from '$lib/dom/scroll-area';
	import {
		arrowOffsetAlong,
		pixels,
		type PaneHead,
		type PaneWidth,
		type Placement,
		type Spot,
		type TriggerProps
	} from './pane';
	import PopoverPanel from './PopoverPanel.svelte';

	/**
	 * What the pane stands by: the control that opens it, drawn by whoever uses the popover, carrying the props it
	 * is handed; or, where nothing on the page is its control, a spot in the area it is drawn in — a name pressed in
	 * the code — which the pane follows while it is open, scrolling with what the area holds. A spot is no control:
	 * what stands there is pressed and picked out as if no pane stood by it.
	 */
	type StandsBy = { trigger: Snippet<[TriggerProps]> } | { at: Spot };

	type Props = StandsBy & {
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
		/** The name the tour lights it by, where the tour stops at it, written with lib/guide/tour.ts's tourStop. */
		'data-tour'?: string | undefined;
		/** A key pressed inside it, for a pane that answers one of its own. */
		onkeydown?: ((event: KeyboardEvent) => void) | undefined;
		children: Snippet;
		/** What stays at its foot while what it holds scrolls: the act it leads to, or what it asks of the reader. */
		foot?: Snippet | undefined;
		/** Whether its foot asks something of the reader, standing apart from the pane on the page's plainest ground. */
		footAsks?: boolean;
	};

	let {
		open = $bindable(),
		label,
		placement,
		width,
		heading,
		aside,
		testId,
		'data-tour': tour,
		onkeydown,
		children,
		foot,
		footAsks = false,
		...standsBy
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

	// What the pane stands by where no control opens it, and its box in the room of the area the pane is drawn in,
	// as it stood when last read
	const at = $derived('at' in standsBy ? standsBy.at : null);
	let spot = $state.raw<AreaBox | null>(null);
	// How far in from the edge the pane lines up with the arrow points: the middle of what it stands by
	const arrowOffset = $derived(open ? arrowOffsetAlong(spot?.width ?? control?.offsetWidth ?? 0) : 0);
	// What heads the pane where it is headed: its heading, and the way to close it as Escape does
	const head = $derived<PaneHead | undefined>(heading === undefined ? undefined : { heading, close, aside });

	const triggerProps = $derived<TriggerProps>({
		'aria-haspopup': 'dialog',
		'aria-expanded': open,
		'aria-controls': open ? paneId : undefined,
		onclick: () => (open = !open),
		[HELD_AS_CONTROL]: holdControl
	});

	/** Move the box the pane stands by to where its spot stands now, in the room of what the box is placed in. */
	function placeSpot() {
		const area = around?.offsetParent;
		const stands = at?.() ?? null;
		if (stands === null || !(area instanceof HTMLElement)) return;
		const read = boxInArea(area, stands);
		// Where it stood is read apart from the fit that asks for this: the pane follows a spot that moved, and is
		// fitted again only as its panel says
		const stood = untrack(() => spot);
		if (stood === null || !sameBox(read, stood)) spot = read;
	}

	// Open by a spot, the pane follows it, read where it stands each frame: its line wraps as the window narrows,
	// and what stands above it grows with nothing scrolled or resized
	$effect(() => {
		if (!open || at === null) return;
		const following = new EveryFrame(placeSpot);
		return () => following.stop();
	});

	/** The control announces itself as it is drawn, and is let go as it goes. */
	function holdControl(element: HTMLElement): () => void {
		control = element;
		return () => (control = undefined);
	}

	// An open pane gives the keyboard to the first of what it holds, unless something in it already has it — a
	// field it opened on. Only where it holds nothing that takes the keyboard does its close take it. It is given
	// without moving the screen: the pane is fitted to stand where the reader sees it, and the browser would
	// scroll the reading area to where what takes the keyboard stood before the fit was drawn
	$effect(() => {
		if (pane && body && !pane.contains(document.activeElement))
			(firstFocusable(body) ?? firstFocusable(pane))?.focus({ preventScroll: true });
	});

	/** Close the pane from the close at its head, as Escape does: the keyboard goes back as it would then. */
	function close() {
		open = false;
	}

	// Opening, it notes what has the keyboard, before the pane is drawn and takes it; closing, or going while
	// open, as a pane by a spot goes with what it stood by, it hands the keyboard back, rather than leave it nowhere
	$effect.pre(() => {
		if (!open) return;
		untrack(noteOpening);
		return () => untrack(handBack);
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

	/** The keyboard went somewhere: to anything outside, which closes the pane; to nothing, which keeps it. */
	function noteKeyboardLeaving(event: FocusEvent) {
		const next = event.relatedTarget;
		if (!(next instanceof Node) || around?.contains(next)) return;
		keyboardHere = false;
		if (open) open = false;
	}

	/**
	 * A key pressed inside the pane: Tab past either end of a pane by a spot closes it, the keyboard going back to
	 * what had it as the pane opened. Such a pane stands apart from its spot in the page's order, at the end of the
	 * area it is drawn in, and Tab would go on from there, far from the spot. Any other key is the pane's own.
	 */
	function answerKey(event: KeyboardEvent) {
		if (at !== null && pane && leavesAtAnEnd(pane, event)) {
			event.preventDefault();
			open = false;
		} else onkeydown?.(event);
	}

	/** Pressing anywhere outside closes the pane, and leaves the keyboard where the reader pressed. */
	function closeIfOutside(event: PointerEvent) {
		if (!open || !around || !(event.target instanceof Node) || around.contains(event.target)) return;
		keyboardHere = false;
		open = false;
	}

	/**
	 * Escape closes the pane, unless something answered it already: a field that asks its question with
	 * Escape, which would otherwise close the question as it opens.
	 */
	function closeOnEscape(event: KeyboardEvent) {
		if (open && event.key === 'Escape' && !event.defaultPrevented && !isComposingText(event)) open = false;
	}
</script>

<svelte:document onpointerdown={closeIfOutside} />
<svelte:window onkeydown={closeOnEscape} />

<div
	bind:this={around}
	class={at === null ? 'relative' : 'cr-ui-popover-spot'}
	style:--cr-spot-left={pixels(spot?.left)}
	style:--cr-spot-top={pixels(spot?.top)}
	style:--cr-spot-width={pixels(spot?.width)}
	style:--cr-spot-height={pixels(spot?.height)}
	onfocusin={() => (keyboardHere = true)}
	onfocusout={noteKeyboardLeaving}
>
	{#if 'trigger' in standsBy}
		{@render standsBy.trigger(triggerProps)}
	{/if}
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
			comesIn
			{arrowOffset}
			{head}
			place={at === null ? undefined : placeSpot}
			{testId}
			onkeydown={answerKey}
			{foot}
			{footAsks}
		>
			{@render children()}
		</PopoverPanel>
	{/if}
</div>
