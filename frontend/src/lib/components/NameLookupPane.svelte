<script lang="ts" generics="From extends AskedFrom">
	import type { Snippet } from 'svelte';
	import { EveryFrame } from '$lib/dom/every-frame';
	import { useReview } from '$lib/review/context';
	import type { AskedFrom, NameLookup } from '$lib/review/name-lookup.svelte';
	import type { NamePlace } from '$lib/types';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Button from '$lib/ui/Button.svelte';
	import EmptyNote from '$lib/ui/EmptyNote.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import Popover from '$lib/ui/Popover.svelte';
	import { answersKey } from './keymap';
	import { firstListed } from './name-places';
	import NameLookupAside from './NameLookupAside.svelte';
	import NameLookupWindow from './NameLookupWindow.svelte';
	import NamePlaces from './NamePlaces.svelte';

	interface Props {
		/** The lookup whose answer the pane shows, of the name asked about where it stands. */
		lookup: NameLookup<From>;
		/** What the pane says at its foot, under what it lists: another way to open it. */
		foot?: Snippet | undefined;
		/** Whether the name asked about is one the change removed, which is why nothing in the code may be called so. */
		removed?: boolean;
	}

	let { lookup, foot, removed = false }: Props = $props();
	const review = useReview();

	// What the pane says while the review reads the repository
	const LOOKING = 'Looking through the repository';

	const asked = $derived(lookup.asked);
	const looked = $derived(asked?.looked ?? null);
	const found = $derived(looked?.kind === 'found' ? looked.found : null);
	// The answer and the place chosen in it, while the answer is read in the window
	const inTheWindow = $derived(
		looked?.kind === 'found' && looked.read.way === 'full' ? { found: looked.found, chosen: looked.read.chosen } : null
	);
	// Open while a name is asked about and not read in the window: the pane notes what had the keyboard as it opens,
	// not as its answer comes
	const open = $derived(asked !== null && inTheWindow === null);
	// The place the window chooses first as it opens; none while the review found none, when it is not offered
	const first = $derived(found === null ? null : firstListed(found));
	// What heads the pane: the word asked about, until the review says what the name is
	const heading = $derived(found?.name ?? asked?.word ?? '');
	let tryAgainButton: HTMLButtonElement | undefined = $state();

	// A failure's act takes the keyboard as the failure is said: the pane holds nothing else to act on
	$effect(() => {
		tryAgainButton?.focus({ preventScroll: true });
	});

	/** Take the reader to a place, the pane put away, the name marked on the line they arrive at. */
	function goTo(place: NamePlace, name: string) {
		lookup.close();
		void review.navigator.goToLine(place.path, { side: 'new', number: place.line }, { column: place.column, name });
	}

	/**
	 * A key of the review pressed in the pane is pressed where the name was asked from. The pane is drawn apart from
	 * that, where nothing round it cuts it, and a key that acts from where the keyboard is — the next line, the file
	 * being read — would act from there. So the keyboard goes back before the review hears the key, which closes the
	 * pane.
	 */
	function pressWhereAsked(event: KeyboardEvent) {
		if (answersKey(review, event)) lookup.keyboardBack();
	}

	// What the pane lists is of the take its name was asked in, and it stands by what it was asked from as that is
	// drawn now: looked for each frame, as nothing tells of a line or a row drawn again. The window looks so for itself
	$effect(() => {
		if (!open) return;
		const watching = new EveryFrame(closeOnceOfThePast);
		return () => watching.stop();
	});

	/** Close a pane of the past: what had the keyboard as the pane opened may be gone. */
	function closeOnceOfThePast() {
		if (!lookup.standsFor(review.diff.takeOnScreen)) lookup.closeToWhereAsked();
	}
</script>

<!-- How many places, and the way to read them in the window, the first listed chosen, once the review found any -->
{#snippet aside()}
	{#if found !== null && first !== null}
		<NameLookupAside {found} readAs="compact" readTheOtherWay={() => lookup.readInTheWindow(first)} />
	{/if}
{/snippet}

<!-- Where a name is defined and used, in a pane by what it was asked from, drawn while the lookup holds the name and
	it is read there: it notes what had the keyboard as it is drawn, and gives the keyboard back as it goes; or in the
	window, read there -->
{#if asked}
	{#if inTheWindow !== null}
		<NameLookupWindow {lookup} found={inTheWindow.found} chosen={inTheWindow.chosen} {goTo} />
	{:else}
		<Popover
			{...asked.from.standsBy}
			bind:open={() => open, (opened) => !opened && lookup.close()}
			label="Where {heading} is defined and used"
			{heading}
			{aside}
			placement="roomier-start"
			width="code"
			testId="name-lookup"
			onkeydown={pressWhereAsked}
			{foot}
		>
			<div class="flex flex-col gap-4 p-3">
				{#if looked?.kind === 'looking'}
					<p data-testid="name-lookup-looking" class="cr-muted flex items-center gap-2 text-xs">
						<BreathingDots tone="quiet" testId="name-lookup-dots" />
						{LOOKING}
					</p>
				{:else if looked?.kind === 'failed'}
					<div class="flex flex-col items-start gap-2">
						<Failure stands="apart" testId="name-lookup-failed" said={looked.why} />
						<Button
							bind:element={tryAgainButton}
							tone="secondary"
							size="xs"
							testId="look-again"
							onclick={() => lookup.tryAgain()}
						>
							Try again
						</Button>
					</div>
				{:else if found !== null && found.places.length === 0}
					<EmptyNote within="list" testId="name-lookup-nothing">
						{#if removed}
							Nothing in the code is called “{found.name}” now: the change removed it.
						{:else}
							Nothing in the code is called “{found.name}”. Here it stands in a comment or a string, or is a word of the
							language.
						{/if}
					</EmptyNote>
				{:else if found !== null}
					{#key found}
						<NamePlaces {found} goTo={(place: NamePlace) => goTo(place, found.name)} />
					{/key}
				{/if}
			</div>
		</Popover>
	{/if}
{/if}
