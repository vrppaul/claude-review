<script lang="ts">
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import EdgeGrip from '$lib/ui/EdgeGrip.svelte';
	import MessageComposer from './MessageComposer.svelte';
	import PanelConversation from './PanelConversation.svelte';
	import PanelStatus from './PanelStatus.svelte';

	const review = useReview();

	// Whether the reader is at the foot of the conversation: the conversation
	// keeps it, and a message sent puts them back there
	let atFoot = $state(true);
</script>

<!-- The conversation about everything a thread is not: who is answering, what has been said, and what is being written -->
<aside
	data-testid="agent-panel"
	data-tour={tourStop('agent-panel')}
	aria-label="The agent"
	class="cr-panel flex min-h-0 flex-col border-l border-base-300"
	style:--cr-panel-width="{review.layout.agentPanel.width}px"
>
	<!-- The panel is on the right, so it grows leftward -->
	<EdgeGrip column={review.layout.agentPanel} grows="left" label="Resize the panel" testId="panel-resize" />
	<PanelStatus />
	<PanelConversation bind:atFoot />
	<div class="shrink-0 border-t border-base-300 px-3 py-2">
		{#if review.answerer.attached}
			<MessageComposer onSending={() => (atFoot = true)} />
		{:else}
			<p data-testid="panel-read-only" class="cr-faint py-1 text-center text-xs">
				You can write here once the agent is listening.
			</p>
		{/if}
	</div>
</aside>
