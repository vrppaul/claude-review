<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Key from '$lib/ui/Key.svelte';
	import { LOOKUP_CHORD, pointerChordName } from './keymap';
	import NameLookupPane from './NameLookupPane.svelte';
	import type { LookupFromTheTree } from './tree-name-lookup';

	interface Props {
		/** Where the names the tree lists are asked about from the icons on their rows. */
		lookup: LookupFromTheTree;
	}

	let { lookup }: Props = $props();
	const review = useReview();

	// The gesture in the code the pane names at its foot, where the code offers it
	const LOOKUP_CHORD_NAME = pointerChordName(LOOKUP_CHORD);

	// Whether the name asked about is one the change removed, which is why nothing in the code may be called so now
	const removed = $derived(lookup.asked?.from.name.change === 'removed');
</script>

<!-- What the pane by a name's icon says at its foot: the gesture that opens it from any name in the code -->
{#snippet gestureInTheCode()}
	<p data-testid="name-lookup-foot" class="cr-muted text-xs">
		<Key keys={LOOKUP_CHORD_NAME} stands="inline" testId="name-lookup-chord" /> on any name in the code opens this.
	</p>
{/snippet}

<!-- Where a name of the tree is defined and used, in a pane by its icon over the column and the code beside it:
	at its foot, where the code offers it, the gesture that opens the same pane from any name in the code -->
<NameLookupPane {lookup} {removed} foot={review.namePointing === null ? undefined : gestureInTheCode} />
