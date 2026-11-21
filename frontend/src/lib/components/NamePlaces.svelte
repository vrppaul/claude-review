<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import type { NamePlace, NameResponse } from '$lib/types';
	import CodeFrame from '$lib/ui/CodeFrame.svelte';
	import CodeFrameLines from '$lib/ui/CodeFrameLines.svelte';
	import CodeFramePath from '$lib/ui/CodeFramePath.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Link from '$lib/ui/Link.svelte';
	import { withNameMarked } from '$lib/utils/code-words';
	import { highlightLine, languageOf } from '$lib/utils/highlight';
	import { type ListedGroup, listedGroups, notesOn } from './name-places';
	import PlaceLine from './PlaceLine.svelte';

	interface Props {
		/** What the review answered of the name: one that stands somewhere. */
		found: NameResponse;
		/** Take the reader to a place. */
		goTo: (place: NamePlace) => void;
	}

	let { found, goTo }: Props = $props();
	const review = useReview();

	const GO_TO_SYMBOL = 'Go to symbol';

	// The groups whose places are all listed, the reader having asked to see the rest
	let shownWhole = $state.raw<ReadonlySet<string>>(new Set());
	const groups = $derived(listedGroups(found, shownWhole));
	// The way to each place listed, in the order they are listed
	const ways: HTMLElement[] = $state([]);

	// The first way to a place takes the keyboard as the places come: the pane holds nothing else to act on
	$effect(() => {
		ways[0]?.focus({ preventScroll: true });
	});

	/** List all of a group, the keyboard on the first place that waited, in place of the way that showed them. */
	function showWhole(group: ListedGroup) {
		shownWhole = new Set([...shownWhole, group.testId]);
		focusWhatRemains(() => ways[group.firstWaiting]);
	}

	/** A place's line as it is listed: from its first word, highlighted as its file is, the name marked where it stands. */
	function lineOf(place: NamePlace): string {
		// Read apart from its file, a line's indent says nothing: it is left off. It is whitespace, a column a unit
		const shown = place.text.trimStart();
		const indent = place.text.length - shown.length;
		const markup = highlightLine(shown, languageOf(review.mode, place.path));
		return withNameMarked(markup, shown, place.column - indent, found.name);
	}
</script>

<!-- Each place of a name, a group to each way it stands, under the files it is in, after what the reader could take
	wrongly from the list -->
{#each notesOn(found) as note (note)}
	<p data-testid="name-lookup-note" class="cr-muted text-xs">{note}</p>
{/each}
{#each groups as group (group.testId)}
	<!-- Its parts a step apart, its files' frames as close, each keeping the room a frame keeps above itself -->
	<section data-testid={group.testId} class="flex flex-col gap-1">
		<div class="flex items-baseline gap-2">
			<Heading tag="h3" heads="list">{group.heading}</Heading>
			<span class="cr-faint text-xs">{group.count}</span>
		</div>
		{#each group.files as file (file.path)}
			<CodeFrame testId="name-places-in-file">
				<CodeFramePath path={file.path} testId="name-places-path" />
				<CodeFrameLines testId="name-places-lines">
					{#each file.places as listed (listed.position)}
						<PlaceLine
							number={listed.place.line}
							markup={lineOf(listed.place)}
							written={listed.place.added}
							testId="name-place"
						>
							{#snippet act()}
								<Link bind:element={ways[listed.position]} testId="go-to-symbol" onclick={() => goTo(listed.place)}>
									{GO_TO_SYMBOL}
								</Link>
							{/snippet}
						</PlaceLine>
					{/each}
				</CodeFrameLines>
			</CodeFrame>
		{/each}
		{#if group.waiting > 0}
			<p class="text-xs">
				<Link testId="show-more-places" onclick={() => showWhole(group)}>Show {group.waiting} more</Link>
			</p>
		{/if}
	</section>
{/each}
