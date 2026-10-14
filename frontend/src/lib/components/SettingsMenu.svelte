<script lang="ts">
	import type { DiffLayout, Theme } from '$lib/types';
	import { useReview } from '$lib/review/context';
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
		<button
			{...control}
			type="button"
			data-testid="settings-toggle"
			class="btn btn-circle btn-ghost btn-sm"
			aria-label="Settings"
			title="Settings"
		>
			<Icon name="settings" class="h-4 w-4" />
		</button>
	{/snippet}

	<div class="flex flex-col gap-2.5 p-3">
		<span class="text-xs font-semibold">Settings</span>

		{#if review.mode === 'diff'}
			<div class="flex items-center justify-between gap-3">
				<span>Diff layout</span>
				<div data-testid="diff-layout-toggle" class="cr-segmented">
					{#each layouts as layout (layout.value)}
						<button
							type="button"
							data-testid={layout.testId}
							class="cr-segment"
							aria-pressed={review.settings.current.diff_layout === layout.value}
							onclick={() => review.settings.change({ diff_layout: layout.value })}
						>
							{layout.label}
						</button>
					{/each}
				</div>
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
			<div data-testid="theme-toggle" class="cr-segmented">
				{#each themes as choice (choice.value)}
					<button
						type="button"
						data-testid={choice.testId}
						class="cr-segment"
						aria-pressed={review.settings.current.theme === choice.value}
						onclick={() => review.settings.change({ theme: choice.value })}
					>
						{choice.label}
					</button>
				{/each}
			</div>
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

		{#if review.story.canBeTold}
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
		{/if}
	</div>
</Popover>
