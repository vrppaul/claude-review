<script lang="ts">
	import type { Snippet } from 'svelte';
	import { tourStop, type TourTarget } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import Column from '$lib/ui/Column.svelte';

	interface Props {
		/** What the tests know the column by: the panel's, or what stands in its place where it could not be drawn. */
		testId: string;
		/** The name the tour lights it by: the panel's, where the tour points at the agent; none in its place. */
		tour?: TourTarget | undefined;
		children: Snippet;
		foot?: Snippet | undefined;
	}

	let { testId, tour, children, foot }: Props = $props();
	const review = useReview();
</script>

<!-- The agent's column, on the right of what is read: as the panel draws it whole, and as what stands in its place
	does where the panel could not be drawn, as wide, so the review beside it does not move -->
<Column
	side="right"
	width={review.layout.agentPanel}
	landmark="aside"
	label="The agent"
	resizing="Resize the panel"
	testIds={{ column: testId, resize: 'panel-resize' }}
	data-tour={tour && tourStop(tour)}
	{foot}
>
	{@render children()}
</Column>
