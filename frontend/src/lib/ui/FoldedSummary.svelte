<script lang="ts">
	import { VOICE_NAMES, type Voice } from './voice';

	// The class of each voice's name: the agent's is said in its colour, the reader's in ink
	const NAMED_IN: Record<Voice, string | null> = { reader: null, agent: 'cr-ui-folded-summary-agent' };

	interface Props {
		/** Who began what the card holds. */
		voice: Voice;
		/** Their first words, cut where the bar runs out of room. */
		words: string;
		testId: string;
	}

	let { voice, words, testId }: Props = $props();
</script>

<!-- What a card folded to its bar holds, said on the bar: who began it, and their first words, which give up room
	to everything else on the bar -->
<span data-testid={testId} class="cr-ui-folded-summary">
	<strong class={NAMED_IN[voice]}>{VOICE_NAMES[voice]}</strong>
	<span class="cr-ui-folded-summary-words">{words}</span>
</span>
