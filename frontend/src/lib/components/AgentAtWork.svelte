<script lang="ts">
	import { useReview } from '$lib/review/context';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Dot from '$lib/ui/Dot.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Turn from '$lib/ui/Turn.svelte';
	import { messageOf } from '$lib/utils/errors';
	import { timeAgo } from '$lib/utils/time';
	import { AGENT_STOPPED_LISTENING, TAKE_BACK } from './agent-waits';
	import FileChip from './FileChip.svelte';

	interface Props {
		/** When the work began: the message that asked for it, or the work itself. */
		since: number;
		/** The message being worked on, which the reader may take back; none for work nobody asked for. */
		messageId?: string | undefined;
	}

	let { since, messageId }: Props = $props();
	const review = useReview();

	let failed = $state<string | null>(null);

	const work = $derived(review.answerer.work);
	// Whether the agent is still there to do it: once it has stopped listening
	// the row says so, rather than go on saying it is at work
	const listening = $derived(review.answerer.attached);

	/** Take back the message being worked on; the agent decides what to do about it. */
	async function takeBack() {
		if (!messageId) return;
		failed = null;
		try {
			await review.conversation.cancel(messageId);
		} catch (error) {
			failed = messageOf(error);
		}
	}
</script>

<!-- The agent at work, a turn of its own on its way, as one awaited in a thread is: how long for, and what it
	says it is doing, replaced as it changes -->
<Turn speaker="agent" testId={messageId ? 'panel-working' : 'panel-work'}>
	{#snippet head()}
		{#if listening}
			<BreathingDots tone="quiet" testId="working-dots" />
		{/if}
		<span class="flex-1"></span>
		<span class="cr-muted">
			{listening ? `working ${timeAgo(since, review.clock.now)}` : AGENT_STOPPED_LISTENING}
		</span>
		{#if messageId}
			<Button tone="secondary" size="xs" testId="stop-message" onclick={takeBack}>{TAKE_BACK}</Button>
		{/if}
	{/snippet}
	<div class="flex flex-col gap-2">
		{#if failed}
			<Failure stands="apart" testId="stop-error" said={failed} />
		{/if}
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
			<div class="flex flex-wrap gap-1">
				<!-- Known by where they stand, since the agent may name a file twice -->
				{#each work.files as path, position (position)}
					<FileChip {path} testId="progress-file" />
				{/each}
			</div>
		{/if}
	</div>
</Turn>
