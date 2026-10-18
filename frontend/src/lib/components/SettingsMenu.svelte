<script lang="ts">
	import type { DiffLayout, Theme } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import IconButton from '$lib/ui/IconButton.svelte';
	import Segment from '$lib/ui/Segment.svelte';
	import Segmented from '$lib/ui/Segmented.svelte';
	import Icon from './Icon.svelte';
	import Popover from './Popover.svelte';

	const review = useReview();

	const layouts: { value: DiffLayout; label: string; testId: string }[] = [
		{ value: 'unified', label: 'Unified', testId: 'layout-unified' },
		{ value: 'split', label: 'Split', testId: 'layout-split' }
	];

	const themes: { value: Theme; label: string; testId: string }[] = [
		{ value: 'system', label: 'System', testId: 'theme-system' },
		{ value: 'light', label: 'Light', testId: 'theme-light' },
		{ value: 'dark', label: 'Dark', testId: 'theme-dark' }
	];

	let open = $state(false);
</script>

<!-- Choices a reader makes once, kept for every review on this machine:
	out of the header, where only what is switched while reading belongs -->
<Popover bind:open label="Settings" placement="below-end" data-testid="settings-menu" class="w-72 text-xs">
	{#snippet trigger(control)}
		<IconButton {...control} tone="quiet" size="sm" label="Settings" data-testid="settings-toggle">
			<Icon name="settings" />
		</IconButton>
	{/snippet}

	<div class="flex flex-col gap-2.5 p-3">
		<span class="text-xs font-semibold">Settings</span>

		{#if review.mode === 'diff'}
			<div class="flex items-center justify-between gap-3">
				<span>Diff layout</span>
				<Segmented label="Diff layout" testId="diff-layout-toggle">
					{#each layouts as layout (layout.value)}
						<Segment
							data-testid={layout.testId}
							pressed={review.settings.current.diff_layout === layout.value}
							onclick={() => review.settings.change({ diff_layout: layout.value })}
						>
							{layout.label}
						</Segment>
					{/each}
				</Segmented>
			</div>

			<label class="flex items-center justify-between gap-3">
				<span>Ignore whitespace</span>
				<input
					data-testid="ignore-whitespace"
					type="checkbox"
					class="checkbox checkbox-xs"
					checked={review.settings.current.ignore_whitespace}
					onchange={(event) => review.setIgnoreWhitespace(event.currentTarget.checked)}
				/>
			</label>
		{/if}

		<div class="flex items-center justify-between gap-3">
			<span>Theme</span>
			<Segmented label="Theme" testId="theme-toggle">
				{#each themes as choice (choice.value)}
					<Segment
						data-testid={choice.testId}
						pressed={review.settings.current.theme === choice.value}
						onclick={() => review.settings.change({ theme: choice.value })}
					>
						{choice.label}
					</Segment>
				{/each}
			</Segmented>
		</div>

		<label class="flex items-center justify-between gap-3">
			<span>
				Tick on a new reply
				<span class="cr-faint block text-xs">only in a background tab</span>
			</span>
			<input
				data-testid="reply-sound"
				type="checkbox"
				class="checkbox checkbox-xs"
				checked={review.settings.current.sound_on_replies}
				onchange={(event) => review.settings.change({ sound_on_replies: event.currentTarget.checked })}
			/>
		</label>

		<!-- Drawn in every review, one no story can be told of too: the choice is the reader's, for all of them -->
		<label class="flex items-center justify-between gap-3">
			<span>
				Stories
				<span class="cr-faint block text-xs">Each story spends the agent's tokens</span>
			</span>
			<input
				data-testid="stories"
				type="checkbox"
				class="checkbox checkbox-xs"
				checked={review.settings.current.stories}
				onchange={(event) => (event.currentTarget.checked ? review.turnStoriesOn() : review.turnStoriesOff())}
			/>
		</label>
	</div>
</Popover>
