<script lang="ts">
	import { commentStore } from '$lib/stores/comments.svelte';
	import { guideStore } from '$lib/stores/guide.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { panelStore } from '$lib/stores/panel.svelte';
	import { reviewStore } from '$lib/stores/review.svelte';
	import { revealThread } from '$lib/anchors/views';
	import BasePicker from './BasePicker.svelte';
	import RepliesMenu from './RepliesMenu.svelte';
	import SettingsMenu from './SettingsMenu.svelte';

	interface Props {
		submitting: boolean;
		error: string | null;
		onOpenModal: () => void;
	}

	let { submitting, error, onOpenModal }: Props = $props();

	// A round is only worth offering while something is there to work through
	// it; on its own, sending is the end of the review
	const inRounds = $derived(reviewStore.canSendRound);

	function step(direction: 1 | -1) {
		const comment = commentStore.step(direction);
		if (!comment) return;

		revealThread(comment);
	}
</script>

<header
	data-testid="top-bar"
	class="flex h-12 shrink-0 items-center gap-3 border-b border-base-300 bg-base-200 px-4"
>
	<span class="font-semibold">Review</span>
	<!-- The ? key may belong to a browser extension, so the list has a button too -->
	<button
		data-testid="open-help"
		class="cr-chip"
		title="The tour, what is new, and the keys (?)"
		onclick={() => guideStore.setHelpOpen(true)}
	>
		<kbd class="cr-guide-key">?</kbd> Help
	</button>
	<!-- What the diff is compared against, as a control. The repository it is
		of is in the tab's title; the header has room only for what changes. -->
	{#if diffStore.phrase}
		<BasePicker />
		{#if diffStore.ignoreWhitespace}
			<!-- Said here as well as in the settings, because it hides changes -->
			<span data-testid="whitespace-hidden" class="cr-chip text-base-content">
				No whitespace
				<button
					data-testid="show-whitespace"
					class="btn btn-ghost btn-xs px-1"
					aria-label="Show whitespace changes again"
					title="Show whitespace changes again"
					onclick={() => diffStore.setIgnoreWhitespace(false)}
				>
					<svg class="h-2.5 w-2.5" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
						<path d="M3 3l6 6M9 3l-6 6" />
					</svg>
				</button>
			</span>
		{/if}
	{:else if diffStore.title}
		<span data-testid="review-title" class="cr-muted truncate font-mono text-xs">
			{diffStore.title}
		</span>
	{/if}

	<div class="flex-1"></div>

	{#if error}
		<span data-testid="submit-error" class="text-sm text-error">{error}</span>
	{/if}

	{#if commentStore.answered.length > 0}
		<RepliesMenu />
	{/if}

	<span data-testid="comment-count" data-tour="unsent-count" class="cr-muted text-sm">
		{#if inRounds}
			{commentStore.unsentCount} unsent · {commentStore.count}
		{:else}
			{commentStore.count}
			{commentStore.count === 1 ? 'comment' : 'comments'}
		{/if}
	</span>

	{#if commentStore.count > 0}
		<div class="join">
			<button
				data-testid="prev-comment"
				class="btn join-item btn-ghost btn-xs"
				onclick={() => step(-1)}
				title="Previous comment"
				aria-label="Previous comment"
			>
				<svg class="h-3 w-3 rotate-180" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
					<path d="M2 4l4 4 4-4z" />
				</svg>
			</button>
			<button
				data-testid="next-comment"
				class="btn join-item btn-ghost btn-xs"
				onclick={() => step(1)}
				title="Next comment"
				aria-label="Next comment"
			>
				<svg class="h-3 w-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
					<path d="M2 4l4 4 4-4z" />
				</svg>
			</button>
		</div>
	{/if}

	<button
		data-testid="toggle-panel" data-tour="agent-panel-toggle"
		class="cr-chip"
		aria-pressed={panelStore.open}
		title="The agent panel — talk about the review, not one line of it"
		onclick={() => panelStore.toggle()}
	>
		<span
			class="h-1.5 w-1.5 rounded-full"
			style="background: {inRounds ? 'var(--cr-add-edge)' : 'var(--color-base-300)'}"
		></span>
		Agent
		{#if panelStore.unread > 0}
			<span data-testid="panel-unread" style="color: var(--cr-mark)">●</span>
		{/if}
	</button>

	<!-- One door: what has been written, a summary, and the two ways out -->
	<button
		class="btn btn-primary btn-sm"
		data-testid="quick-submit" data-tour="send"
		disabled={submitting}
		onclick={onOpenModal}
		title="Ctrl+Shift+Enter"
	>
		{#if submitting}
			<span class="loading loading-xs loading-spinner"></span>
			Sending
		{:else if inRounds}
			Send round {reviewStore.round}
		{:else}
			Finish review
		{/if}
		<svg class="h-2.5 w-2.5" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
			<path d="M2 4l4 4 4-4z" />
		</svg>
	</button>

	<SettingsMenu />
</header>
