<script lang="ts">
	import { useReview } from '$lib/review/context';
	import EdgeGrip from './EdgeGrip.svelte';
	import MessageComposer from './MessageComposer.svelte';
	import PanelConversation from './PanelConversation.svelte';
	import PanelStatus from './PanelStatus.svelte';

	const review = useReview();

	// Whether the reader is at the foot of the conversation: the conversation
	// keeps it, and a message sent puts them back there
	let atFoot = $state(true);

	/** The panel is on the right, so dragging left is what widens it. */
	const sizing = $derived({
		width: review.layout.agentPanel.width,
		grows: 'left' as const,
		onWidth: (width: number) => review.layout.agentPanel.setWidth(width)
	});
</script>

<!-- The conversation about everything a thread is not: who is answering, what has been said, and what is being written -->
<aside
	data-testid="agent-panel"
	data-tour="agent-panel"
	class="cr-panel flex min-h-0 shrink-0 flex-col border-l border-base-300"
	style:--cr-panel-width="{review.layout.agentPanel.width}px"
>
	<EdgeGrip {sizing} label="Resize the panel" testId="panel-resize" />
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
