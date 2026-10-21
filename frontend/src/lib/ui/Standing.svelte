<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * What it says, by the colour it is said in:
	 * - quiet: where a thing stands and nothing more, "sent in round 1"
	 * - done: settled, "resolved"
	 * - agent: the agent at work on it, "answering"
	 * - unread: something new nobody has looked at, "new reply"
	 * - faint: how much there is of it, "2 replies"
	 */
	type StandingTone = 'quiet' | 'done' | 'agent' | 'unread' | 'faint';

	// The class of each in the library's stylesheet
	const STANDING_TONES: Record<StandingTone, string> = {
		quiet: 'cr-ui-standing-quiet',
		done: 'cr-ui-standing-done',
		agent: 'cr-ui-standing-agent',
		unread: 'cr-ui-standing-unread',
		faint: 'cr-ui-standing-faint'
	};

	interface Props {
		tone: StandingTone;
		testId: string;
		/** Its mark, if it has one — a check, breathing dots, a dot — and its words. */
		children: Snippet;
	}

	let { tone, testId, children }: Props = $props();
</script>

<!-- A few small words of where a thing stands, on a bar's line, never wrapped: what only says, so no control -->
<span data-testid={testId} class={['cr-ui-standing', STANDING_TONES[tone]]}>{@render children()}</span>
