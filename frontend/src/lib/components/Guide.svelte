<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { anyOnPage, reveal } from '$lib/guide/spotlight';
	import { useReview } from '$lib/review/context';
	import GuideCard from './GuideCard.svelte';
	import TourSpotlight from './TourSpotlight.svelte';

	const review = useReview();

	const step = $derived(review.guide.step);

	// The page is what knows which steps have something to show, and the
	// comment fields are what know how a comment went. The tour hears them
	// once the page has drawn the result, so the step it moves to finds it.
	onMount(() => {
		review.guide.readPageWith(anyOnPage);
		return review.commentFields.listen((event) => void tick().then(() => review.guide.notice(event)));
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
<GuideCard />
