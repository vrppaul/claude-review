<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	// What heads the line that says what was done
	const TAKEN_BACK = 'Taken back.';

	interface Props {
		/** What came of it, said after that it was taken back: "The agent was asked to drop it." */
		said: string;
		/** The test id of the line that says it. */
		testId: string;
		/** What was taken back, as it was said: struck through, and still read. */
		children: Snippet;
	}

	let { said, testId, children }: Props = $props();
</script>

<!-- What the reader asked for and took back stays seen where it happened, in a thread or in the panel: its words
	struck through, and under them a line of its own, in the colour of what cannot be undone, saying what was done -->
<div class="cr-ui-taken-back-words">{@render children()}</div>
<p data-testid={testId} class="cr-ui-taken-back">
	<Icon name="taken-back" size="sm" tone="danger" />
	<span><span class="cr-ui-taken-back-what">{TAKEN_BACK}</span> {said}</span>
</p>
