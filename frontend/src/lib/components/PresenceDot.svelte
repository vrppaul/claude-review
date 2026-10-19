<script lang="ts">
	import { useReview } from '$lib/review/context';
	import type { DotTone } from '$lib/ui/dot';
	import Dot from '$lib/ui/Dot.svelte';

	/** How the agent stands with the review, as far as the page can tell. */
	type Presence = 'absent' | 'working' | 'listening';
	// Each in its own colour: at work in the agent's, listening in the colour of something ready
	const TONES: Record<Presence, DotTone> = {
		absent: 'absent',
		working: 'agent',
		listening: 'done'
	};

	const review = useReview();

	// While the review cannot be reached, the page cannot tell whether the agent is still there
	const presence = $derived<Presence>(
		!review.link.connected || !review.answerer.attached
			? 'absent'
			: review.conversation.working
				? 'working'
				: 'listening'
	);
</script>

<!-- How the agent stands with the review, the same dot wherever it is said; words beside it say it aloud -->
<Dot tone={TONES[presence]} testId="presence-dot" />
