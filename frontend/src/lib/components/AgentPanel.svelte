<script lang="ts">
	import { useReview } from '$lib/review/context';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Count from '$lib/ui/Count.svelte';
	import SpeakerMark from '$lib/ui/SpeakerMark.svelte';
	import { counted, type CountedWords } from '$lib/utils/words';
	import AgentColumn from './AgentColumn.svelte';
	import MessageComposer from './MessageComposer.svelte';
	import PanelConversation from './PanelConversation.svelte';
	import PanelStatus from './PanelStatus.svelte';
	import PanelWeights from './PanelWeights.svelte';
	import PresenceDot from './PresenceDot.svelte';

	// What the figure on the rail counts, said under the pointer
	const UNREAD: CountedWords = { one: 'reply unread', many: 'replies unread' };

	const review = useReview();
	const unread = $derived(review.layout.agentPanel.unread);

	// Whether the reader is at the foot of the conversation: the conversation
	// keeps it, and a message sent puts them back there
	let atFoot = $state(true);
</script>

<!-- The conversation about everything a thread is not: who is answering, what has been said, and what is being
	written. It takes the right edge and what is read keeps the rest, as what is discussed has to stay on screen;
	put away, its rail says whether the agent is there, at work, and how many of its replies wait unread -->
<AgentColumn testId="agent-panel" tour="agent-panel">
	{#snippet heading()}
		<PanelStatus />
	{/snippet}
	{#snippet marks()}
		<SpeakerMark speaker="agent">
			{#snippet corner()}
				<PresenceDot />
			{/snippet}
		</SpeakerMark>
		<!-- At work as the panel draws it: on a message the reader sent, or on work nobody asked for -->
		{#if review.conversation.working || review.answerer.work}
			<BreathingDots tone="quiet" stacked testId="panel-rail-working" />
		{/if}
		{#if unread > 0}
			<Count tone="unread" count={unread} title={counted(unread, UNREAD)} testId="panel-rail-unread" />
		{/if}
	{/snippet}
	<PanelWeights />
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
