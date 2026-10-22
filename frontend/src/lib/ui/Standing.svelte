<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * What it says, by the colour it is said in:
	 * - quiet: where a thing stands and nothing more, "sent in round 1"
	 * - done: settled, "resolved"
	 * - agent: the agent at work on it, "answering"; the round a story was told in, while its code is current
	 * - unread: something new nobody has looked at, "new reply"
	 * - faint: how much there is of it, "2 replies"
	 * - warning: what to look at, a story whose code moved on under it
	 */
	type StandingTone = 'quiet' | 'done' | 'agent' | 'unread' | 'faint' | 'warning';

	/**
	 * Where it stands, which sets the size of its words:
	 * - on-a-bar: on the line of a card's bar, at the size of the bar's small words
	 * - under-a-heading: under the title it says something of, a step smaller, so the title reads first
	 */
	type StandingPlace = 'on-a-bar' | 'under-a-heading';

	// The class of each in the library's stylesheet
	const STANDING_TONES: Record<StandingTone, string> = {
		quiet: 'cr-ui-standing-quiet',
		done: 'cr-ui-standing-done',
		agent: 'cr-ui-standing-agent',
		unread: 'cr-ui-standing-unread',
		faint: 'cr-ui-standing-faint',
		warning: 'cr-ui-standing-warning'
	};

	const STANDING_PLACES: Record<StandingPlace, string> = {
		'on-a-bar': 'cr-ui-standing-on-a-bar',
		'under-a-heading': 'cr-ui-standing-under-a-heading'
	};

	interface Props {
		tone: StandingTone;
		stands: StandingPlace;
		testId: string;
		/** Its mark, if it has one — a check, breathing dots, a dot, a round — and its words. */
		children: Snippet;
	}

	let { tone, stands, testId, children }: Props = $props();
</script>

<!-- A few small words of where a thing stands, on a bar's line or under a title, never wrapped: what only says, so
	no control -->
<span data-testid={testId} class={['cr-ui-standing', STANDING_TONES[tone], STANDING_PLACES[stands]]}
	>{@render children()}</span
>
