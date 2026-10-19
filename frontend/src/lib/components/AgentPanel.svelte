<script lang="ts">
	import { useReview } from '$lib/review/context';
	import AgentColumn from './AgentColumn.svelte';
	import MessageComposer from './MessageComposer.svelte';
	import PanelConversation from './PanelConversation.svelte';
	import PanelStatus from './PanelStatus.svelte';

	const review = useReview();

	// Whether the reader is at the foot of the conversation: the conversation
	// keeps it, and a message sent puts them back there
	let atFoot = $state(true);
</script>

<!-- The conversation about everything a thread is not: who is answering, what has been said, and what is being
	written. It takes the right edge and what is read keeps the rest, as what is discussed has to stay on screen -->
<AgentColumn testId="agent-panel" tour="agent-panel">
	<PanelStatus />
	<PanelConversation bind:atFoot />
	{#snippet foot()}
		{#if review.answerer.attached}
			<MessageComposer onSending={() => (atFoot = true)} />
		{:else}
			<p data-testid="panel-read-only" class="cr-faint py-1 text-center text-xs">
				You can write here once the agent is listening.
			</p>
		{/if}
	{/snippet}
</AgentColumn>
