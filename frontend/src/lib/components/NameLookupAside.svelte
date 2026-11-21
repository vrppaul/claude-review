<script lang="ts">
	import type { AnswerRead } from '$lib/review/name-lookup.svelte';
	import type { NameResponse } from '$lib/types';
	import Segment from '$lib/ui/Segment.svelte';
	import Segmented from '$lib/ui/Segmented.svelte';
	import { countSaid } from './name-places';

	interface Props {
		/** What the review found of the name: one that stands somewhere. */
		found: NameResponse;
		/** How the answer is read now, which its segment says. */
		readAs: AnswerRead['way'];
		/** Read it the other way. */
		readTheOtherWay: () => void;
	}

	let { found, readAs, readTheOtherWay }: Props = $props();
</script>

<!-- What stands beside the name in the head of its pane and of its window: how many places, and the two ways to
	read them, the way read now pressed -->
<span data-testid="name-lookup-count" class="cr-faint text-xs">{countSaid(found)}</span>
<Segmented label="How to read where the name stands" size="xs" testId="answer-read">
	<Segment
		testId="read-compact"
		pressed={readAs === 'compact'}
		onclick={readAs === 'compact' ? undefined : readTheOtherWay}
	>
		Compact
	</Segment>
	<Segment testId="read-full" pressed={readAs === 'full'} onclick={readAs === 'full' ? undefined : readTheOtherWay}>
		Full
	</Segment>
</Segmented>
