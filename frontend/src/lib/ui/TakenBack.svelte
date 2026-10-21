<script lang="ts">
	import Icon from './Icon.svelte';
	import TurnAside from './TurnAside.svelte';

	// What heads the line that says what was done
	const TAKEN_BACK = 'Taken back';

	interface Props {
		/** How long ago it was taken back, in words: "40s ago". */
		ago: string;
		/** What came of it, said after when: "The agent was asked to drop it." */
		said: string;
		/** The test id of the line that says it. */
		testId: string;
	}

	let { ago, said, testId }: Props = $props();
</script>

<!-- What the reader asked for and took back stays seen where it happened, in a thread or in the panel: its words
	struck through in their turn (Turn's takenBack), and under it this line of the conversation, on the tint of what
	cannot be undone, its mark in that colour, saying what was done and when -->
<TurnAside lays="taken-back" {testId}>
	<Icon name="taken-back" size="sm" tone="danger" />
	<span><strong class="cr-ui-taken-back-what">{TAKEN_BACK}</strong> {ago}. {said}</span>
</TurnAside>
