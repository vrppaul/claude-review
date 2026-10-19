<script lang="ts">
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import Column from '$lib/ui/Column.svelte';
	import { AGENT_COLUMN } from './agent-column';
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
<Column
	{...AGENT_COLUMN}
	width={review.layout.agentPanel}
	testIds={{ column: 'agent-panel', resize: 'panel-resize' }}
	data-tour={tourStop('agent-panel')}
>
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
</Column>
