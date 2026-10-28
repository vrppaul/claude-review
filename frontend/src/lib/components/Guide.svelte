<script lang="ts">
	import { onMount, tick, untrack } from 'svelte';
	import { reveal, TargetWatcher } from '$lib/guide/spotlight';
	import { TOUR_TARGETS } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import PointedRing from '$lib/ui/PointedRing.svelte';
	import { stopsTogether } from '$lib/utils/stops';
	import GuideCard from './GuideCard.svelte';
	import TourSpotlight from './TourSpotlight.svelte';

	const review = useReview();

	const step = $derived(review.guide.step);

	// The comment fields are what know how a comment went. The tour hears them
	// as it happens, and moves on once the page says it has drawn what came of it.
	onMount(() => review.commentFields.listen((event) => review.guide.notice(event)));

	// The page is what knows which steps have something to show. It is
	// watched while the tour runs, or while the welcome or the ? list says
	// how many stops the tour has, and only then: watching looks over the
	// page on every change, and nothing else asks.
	$effect(() => {
		if (!review.guide.watchesThePage) return;
		// What the watcher tells the guide is not what this effect follows
		const drawn = untrack(() => new TargetWatcher(TOUR_TARGETS, (targets) => review.guide.seeTargets(targets)));
		return stopsTogether(
			() => drawn.stop(),
			() => review.guide.pageUnwatched()
		);
	});

	// A step's place is brought into view once it is drawn, which is after
	// the step changes, not as it does
	$effect(() => {
		const shown = step;
		if (!shown) return;
		void tick().then(() => reveal(shown.targets));
	});
</script>

<!-- No key of its own to leave by: Escape belongs to whatever is open over
	the review, and the card's Skip is one click -->
{#if step}
	<TourSpotlight targets={step.targets} />
{/if}
<!-- The part the reader points at for their feedback, ringed beside the card they point from, never over it -->
{#if review.feedback.over}
	<PointedRing part={review.feedback.over} testId="feedback-pointed" />
{/if}
<GuideCard />
