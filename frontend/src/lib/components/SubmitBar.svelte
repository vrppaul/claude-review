<script lang="ts">
	import { onMount } from 'svelte';
	import FinishReview from './FinishReview.svelte';
	import TopBar from './TopBar.svelte';
	import { useReview } from '$lib/review/context';
	import { messageOf } from '$lib/utils/errors';
	import Icon from './Icon.svelte';

	// What the header says when the review could not be sent, and nothing said why
	const SENDING_FAILED = 'Could not send the review';

	const review = useReview();

	let submitting = $state(false);
	let failed = $state<string | null>(null);
	let showModal = $state(false);

	async function handleSubmit() {
		await send(() => review.submission.submit(true), { closes: true });
	}

	/**
	 * Send what has been written and keep reading.
	 *
	 * The tab stays: the threads are still on screen, which is where the
	 * answers to this round come back to.
	 */
	async function handleSendRound() {
		await send(() => review.submission.submit(false), { closes: false });
	}

	async function handleEnd() {
		await send(() => review.submission.end(), { closes: true });
	}

	async function send(act: () => Promise<unknown>, { closes }: { closes: boolean }) {
		if (submitting) return;
		submitting = true;
		failed = null;
		try {
			await act();
			showModal = false;
			if (closes) window.close();
		} catch (error) {
			failed = messageOf(error, SENDING_FAILED);
		} finally {
			submitting = false;
		}
	}

	onMount(() => {
		function onKeydown(e: KeyboardEvent) {
			if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && e.shiftKey) {
				if (showModal) return; // the popover handles its own shortcut
				e.preventDefault();
				showModal = true;
			}
		}
		window.addEventListener('keydown', onKeydown);
		return () => window.removeEventListener('keydown', onKeydown);
	});
</script>

{#if review.submission.finished}
	<div
		data-testid="submitted-banner"
		class="flex h-12 shrink-0 items-center justify-center gap-3 border-b border-base-300 bg-base-200 px-4"
	>
		<Icon name="check" class="h-4 w-4" style="color: var(--cr-mark)" />
		<p class="font-semibold">Review sent. You can close this tab.</p>
	</div>
{:else}
	<div class="relative">
		<TopBar {submitting} error={failed} onOpenModal={() => (showModal = true)} />

		{#if showModal}
			<FinishReview
				{submitting}
				onSubmit={handleSubmit}
				onSendRound={handleSendRound}
				onEnd={handleEnd}
				onClose={() => (showModal = false)}
			/>
		{/if}
	</div>
{/if}
