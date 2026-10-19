<script lang="ts">
	import Heading from './Heading.svelte';

	interface Props {
		/** What the pane asks, as it is named by: "Discard this comment?" */
		question: string;
		testId: string;
	}

	let { question, testId }: Props = $props();
</script>

<!-- What a pane that asks a question asks, first in it and as every pane's heading is: it heads the pane,
	which has no head of its own, as its answers are its ways out -->
<Heading tag="h2" heads="pane" {testId}>{question}</Heading>
