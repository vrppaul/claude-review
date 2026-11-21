<script lang="ts" generics="From extends AskedFrom">
	import { untrack } from 'svelte';
	import { EveryFrame } from '$lib/dom/every-frame';
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import type { AskedFrom, NameLookup } from '$lib/review/name-lookup.svelte';
	import { PlacesCode } from '$lib/review/places-code.svelte';
	import type { NamePlace, NameResponse } from '$lib/types';
	import Actions from '$lib/ui/Actions.svelte';
	import Button from '$lib/ui/Button.svelte';
	import CodeFramePath from '$lib/ui/CodeFramePath.svelte';
	import Dialog from '$lib/ui/Dialog.svelte';
	import type { Closing } from '$lib/ui/dialog-closing';
	import PaneColumns from '$lib/ui/PaneColumns.svelte';
	import NameLookupAside from './NameLookupAside.svelte';
	import NamePlaces from './NamePlaces.svelte';
	import PlaceCode from './PlaceCode.svelte';

	interface Props {
		/** The lookup that holds what the window shows. */
		lookup: NameLookup<From>;
		/** What the review found of the name: one that stands somewhere. */
		found: NameResponse;
		/** The place chosen, whose code stands beside the list. */
		chosen: NamePlace;
		/** Take the reader to a place, the name marked on its line. */
		goTo: (place: NamePlace, name: string) => void;
	}

	let { lookup, found, chosen, goTo }: Props = $props();
	const review = useReview();

	// What the code's head says of the place: whether the change wrote its line
	const IN_THIS_CHANGE = 'in this change';
	const NOT_IN_THIS_CHANGE = 'not in this change';

	// The code round the places, each file read once while the window is open
	const code = new PlacesCode(review.mode);
	// Whether the window stands open: it closes as its own ways close it once what it shows is of the past
	let open = $state(true);
	// Whether its closing brings the pane back by the name, the reader having asked to read it there
	let backToThePane = false;
	// The way to the place chosen in the list, which takes the keyboard where an act beside it goes
	let chosenWay: HTMLElement | undefined = $state();

	// The file of the place chosen is read as it is chosen, and only then: a read that failed is read again at the
	// reader's word
	$effect(() => {
		const path = chosen.path;
		untrack(() => code.read(path));
	});

	// What the window shows is of the take its name was asked in, while what it was asked from is drawn: looked for
	// each frame, as nothing tells of a line or a row drawn again
	$effect(() => {
		const watching = new EveryFrame(closeOnceOfThePast);
		return () => watching.stop();
	});

	/** Close a window of the past, as its own ways close it. */
	function closeOnceOfThePast() {
		if (!lookup.standsFor(review.diff.takeOnScreen)) open = false;
	}

	/**
	 * Read the file of the place chosen again, after a read that failed. The act goes as the code comes, so the way
	 * to the place chosen takes the keyboard, as the reader is walking the places.
	 */
	function readAgain(path: string) {
		code.read(path);
		focusWhatRemains(() => chosenWay);
	}

	/** Close the window, and bring the pane back by the name, the same answer in it. */
	function readInThePane() {
		backToThePane = true;
		open = false;
	}

	/**
	 * Close the window, and then take the reader to a place. The name is read first: the lookup ends as the window
	 * closes, and what it held goes with it.
	 */
	function goingTo(place: NamePlace, { closeThen }: Closing) {
		const name = found.name;
		closeThen(() => goTo(place, name));
	}

	/**
	 * The window has closed, the keyboard on nothing: the browser gives it back to what had it as the window opened,
	 * the pane's Full, gone with the pane. The pane comes back where the reader asked for it, or the lookup is over;
	 * either way the keyboard goes to where the name was asked from.
	 */
	function closed() {
		if (backToThePane) lookup.readInThePane();
		else lookup.closeToWhereAsked();
	}
</script>

{#snippet aside()}
	<NameLookupAside {found} readAs="full" readTheOtherWay={readInThePane} />
{/snippet}

<!-- The one act the window leads to, at its foot: to the place chosen, as each place's own way goes -->
{#snippet foot(closing: Closing)}
	<Actions testId="name-window-actions">
		{#snippet main()}
			<Button tone="primary" size="sm" testId="go-to-chosen-symbol" onclick={() => goingTo(chosen, closing)}>
				Go to symbol
			</Button>
		{/snippet}
	</Actions>
{/snippet}

<!-- Where a name is defined and used, read in a window over the page: the places listed as the pane lists them,
	one chosen at all times, and the code round it beside them. Each way to a place closes the window first, so the
	keyboard is back on the page before the reader is taken there -->
<Dialog
	label="Where {found.name} is defined and used"
	heading={found.name}
	{aside}
	width="window"
	{open}
	testId="name-lookup-window"
	onClose={closed}
	{foot}
>
	{#snippet children(closing: Closing)}
		<PaneColumns testId="name-window-columns" besideLabel="The code round {chosen.path}:{chosen.line}">
			{#snippet list()}
				<div class="flex flex-col gap-4 p-3">
					<NamePlaces
						bind:chosenWay
						{found}
						goTo={(place: NamePlace) => goingTo(place, closing)}
						choosing={{ chosen, choose: (place: NamePlace) => lookup.readInTheWindow(place) }}
					/>
				</div>
			{/snippet}
			<!-- What heads the code: its file and what the place stands inside, and whether the change wrote the line,
				as the list beside it groups the place -->
			{#snippet besideHead()}
				<CodeFramePath
					path={chosen.path}
					within={chosen.inside}
					said={chosen.added ? IN_THIS_CHANGE : NOT_IN_THIS_CHANGE}
					testId="name-window-path"
				/>
			{/snippet}
			{#snippet beside()}
				<PlaceCode
					place={chosen}
					name={found.name}
					read={code.of(chosen.path)}
					readAgain={() => readAgain(chosen.path)}
				/>
			{/snippet}
		</PaneColumns>
	{/snippet}
</Dialog>
