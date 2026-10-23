<script lang="ts">
	import type { Snippet } from 'svelte';
	import FoldChevron from './FoldChevron.svelte';
	import { foldToggleName } from './fold';
	import Heading from './Heading.svelte';
	import Icon from './Icon.svelte';
	import type { IconName } from './icons';
	import Tag from './Tag.svelte';

	interface Props {
		/** What kind of list it is, drawn before its name. */
		icon: IconName;
		/** What the list is called: the heading it stands under, to whoever goes through the page by its headings. */
		name: string;
		/** How many items it holds, said beside its name: a list of one may stand as that one item. */
		count: number;
		/** The words of its first item: the line it folds to, cut where the line ends. */
		firstWords: string;
		/** Why it stays open, said on the pointer, while something hangs in it; none while the reader may fold it. */
		heldOpenBecause: string | undefined;
		/** Its test id; its fold, its count and the line it folds to are known by this followed by `-toggle`, `-count`, `-line`. */
		testId: string;
		/** Its items, each an `<li>`. */
		children: Snippet;
	}

	let { icon, name, count, firstWords, heldOpenBecause, testId, children }: Props = $props();

	// Whether the reader opened it; one held open by what hangs in it is open whatever they pressed
	let openedByReader = $state(false);
	const open = $derived(openedByReader || heldOpenBecause !== undefined);
	// The line it would fold to, and the words of its one item laid on one line, as the browser lays them out
	let lineWidth = $state(0);
	let wordsWidth = $state(0);
	// A list of one item whose words fit the line it would fold to is that item, with nothing to fold. Narrower,
	// not as wide: both widths come rounded to whole pixels, so words as wide as the line may run past it
	const fits = $derived(count === 1 && wordsWidth < lineWidth);

	/** A press on its fold opens it or folds it, but folds nothing while something hangs in it. */
	function toggle() {
		if (heldOpenBecause === undefined) openedByReader = !openedByReader;
	}
</script>

<!-- One list of a card of lists (ListsCard): its mark, its name and how many it holds, then its items in full, or,
	folded, the first one's words on one line. Folded, the whole row is its fold, one press that opens it; open, its
	fold is the chevron alone, on the same spot. A list of one item whose words fit the line is that item, and
	folds no more until the line is too short for them -->
<div data-testid={testId} class="cr-ui-lists-row">
	<div class="cr-ui-lists-row-name">
		<Icon name={icon} size="sm" tone="agent" />
		<Heading tag="h3" heads="pane">{name}</Heading>
		<Tag tone="quiet" testId="{testId}-count">{count}</Tag>
	</div>
	<!-- Its fold before what it opens, though drawn at the row's end: the next key after opening it goes in -->
	{#if !fits}
		<button
			type="button"
			data-testid="{testId}-toggle"
			class={['cr-ui-lists-row-fold', open ? 'cr-pressable' : 'cr-ui-lists-row-fold-whole-row']}
			aria-expanded={open}
			aria-label={foldToggleName(!open, name)}
			aria-disabled={heldOpenBecause !== undefined}
			title={heldOpenBecause}
			onclick={toggle}
		>
			<FoldChevron folded={!open} />
		</button>
	{/if}
	{#if open || fits}
		<!-- Opened by the reader's press, its items come down over a fold's time; held open or fitting, they stand -->
		<ul class={['cr-ui-lists-row-items', openedByReader && 'cr-ui-unfolding']}>{@render children()}</ul>
	{:else}
		<p data-testid="{testId}-line" class="cr-ui-lists-row-line">{firstWords}</p>
	{/if}
	{#if count === 1}
		<!-- The line it would fold to, unseen, its one item's words on it, measured -->
		<p class="cr-ui-lists-row-line cr-ui-lists-row-measure" aria-hidden="true" bind:clientWidth={lineWidth}>
			<span bind:offsetWidth={wordsWidth}>{firstWords}</span>
		</p>
	{/if}
</div>
