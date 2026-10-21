<script lang="ts">
	import type { Snippet } from 'svelte';
	import { tourStop, type TourTarget } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import SideColumn from '$lib/ui/SideColumn.svelte';
	import { TALK_KEY } from './keymap';

	interface Props {
		/** What the tests know the column by: the panel's, or what stands in its place where it could not be drawn. */
		testId: string;
		/** The name the tour lights it by: the panel's, where the tour points at the agent; none in its place. */
		tour?: TourTarget | undefined;
		heading: Snippet;
		marks?: Snippet | undefined;
		children: Snippet;
		foot?: Snippet | undefined;
	}

	let { testId, tour, heading, marks, children, foot }: Props = $props();
	const review = useReview();
</script>

<!-- The agent's column, on the right of what is read, put away to its rail as the tree is: as the panel draws it
	whole, and as what stands in its place does where the panel could not be drawn, as wide, so the review beside it
	does not move -->
<SideColumn
	column={review.layout.agentPanel}
	side="right"
	landmark="aside"
	label="The agent"
	called="the agent"
	resizing="Resize the panel"
	key={TALK_KEY}
	holds="parts"
	data-tour={tour && tourStop(tour)}
	testIds={{
		column: testId,
		head: 'panel-status',
		resize: 'panel-resize',
		putAway: 'close-panel',
		bringBack: 'show-panel'
	}}
	{heading}
	{marks}
	{foot}
>
	{@render children()}
</SideColumn>
