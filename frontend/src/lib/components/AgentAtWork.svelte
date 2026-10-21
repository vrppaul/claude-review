<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import Dot from '$lib/ui/Dot.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import { timeAgo } from '$lib/utils/time';
	import AgentOnItsWay from './AgentOnItsWay.svelte';
	import FileChip from './FileChip.svelte';

	interface Props {
		/** When the work began: the message that asked for it, or the work itself. */
		since: number;
		/** The message being worked on, which the reader may take back; none for work nobody asked for. */
		messageId?: string | undefined;
		/** What takes the keyboard once the message is taken back and this turn goes: the conversation it stood in. */
		whatRemains?: (() => HTMLElement | null) | undefined;
	}

	let { since, messageId, whatRemains }: Props = $props();
	const review = useReview();

	const work = $derived(review.answerer.work);
	// Only a message the reader sent can be taken back; the agent decides what to do about it
	const takeBack = $derived(messageId === undefined ? undefined : () => takeBackAndStay(messageId));

	/** Take the message back; this turn goes with it, and the keyboard stays in the conversation, never on nothing. */
	async function takeBackAndStay(message: string) {
		await review.conversation.cancel(message);
		focusWhatRemains(() => whatRemains?.());
	}
</script>

<!-- The agent at work in the panel, as an answer awaited in a thread is: what it says it is doing, replaced as
	it changes -->
<AgentOnItsWay
	testId={messageId === undefined ? 'panel-work' : 'panel-working'}
	waited={timeAgo(since, review.clock.now)}
	{takeBack}
>
	{#if work?.text}
		<p data-testid="panel-progress" class="cr-progress text-sm">{work.text}</p>
	{/if}
	{#if work && work.steps.length > 0}
		<!-- Branches of the same work, drawn hanging off it: known by where they
			stand, since the agent may name the same step twice -->
		<ul data-testid="progress-steps" class="cr-branches">
			{#each work.steps as step, position (position)}
				<li class={['cr-branch', step.done && 'cr-branch-done']}>
					{#if step.done}
						<span class="cr-branch-mark"><Icon name="check" size="xs" tone="done" /></span>
					{:else}
						<span class="cr-branch-mark"><Dot tone="quiet" breathing testId="branch-running" /></span>
					{/if}
					<span>{step.text}</span>
				</li>
			{/each}
		</ul>
	{/if}
	{#if work && work.files.length > 0}
		<!-- As far under what it says as the files of the agent's answer stand under its words -->
		<div class="mt-2 flex flex-wrap gap-1">
			<!-- Known by where they stand, since the agent may name a file twice -->
			{#each work.files as path, position (position)}
				<FileChip {path} testId="progress-file" />
			{/each}
		</div>
	{/if}
</AgentOnItsWay>
