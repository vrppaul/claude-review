<script lang="ts">
	import { useReview } from '$lib/review/context';

	/** How the agent stands with the review. */
	type Presence = 'absent' | 'working' | 'listening';
	// Each in its own colour: at work in the agent's, listening in the colour of something ready
	const DOTS: Record<Presence, string> = {
		absent: 'bg-base-300',
		working: 'bg-(--cr-agent)',
		listening: 'bg-(--cr-done)'
	};

	const review = useReview();

	const presence = $derived<Presence>(
		!review.answerer.attached ? 'absent' : review.conversation.working ? 'working' : 'listening'
	);
</script>

<!-- How the agent stands with the review, the same dot wherever it is said; words beside it say it aloud -->
<span class={['h-1.5 w-1.5 shrink-0 rounded-full', DOTS[presence]]} aria-hidden="true"></span>
