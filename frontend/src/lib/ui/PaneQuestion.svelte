<script lang="ts">
	interface Props {
		/** What the pane asks, as it is named by: "Discard this comment?" */
		question: string;
		testId: string;
	}

	let { question, testId }: Props = $props();
</script>

<!-- What a pane that asks a question asks, first in it and at the size of every pane's heading: it heads the pane,
	which has no head of its own, as its answers are its ways out -->
<h2 data-testid={testId} class="cr-ui-pane-question">{question}</h2>
