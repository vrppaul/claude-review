<script lang="ts">
	import type { DiffLayout, Theme } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import Checkbox from '$lib/ui/Checkbox.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import Segment from '$lib/ui/Segment.svelte';
	import Segmented from '$lib/ui/Segmented.svelte';
	import Setting from '$lib/ui/Setting.svelte';
	import Popover from './Popover.svelte';

	// What the pane is called, and headed with, and what its control says to whoever cannot see the gear
	const SETTINGS = 'Settings';

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
<Popover bind:open label={SETTINGS} heading={SETTINGS} placement="below-end" width="medium" testId="settings-menu">
	{#snippet trigger(control)}
		<IconButton {...control} tone="quiet" size="sm" label={SETTINGS} testId="settings-toggle">
			<Icon name="settings" size="base" />
		</IconButton>
	{/snippet}

	<div class="flex flex-col gap-2 p-3 text-xs">
		{#if review.mode === 'diff'}
			<Setting label="Diff layout" testId="diff-layout-setting">
				<Segmented label="Diff layout" testId="diff-layout-toggle">
					{#each layouts as layout (layout.value)}
						<Segment
							testId={layout.testId}
							pressed={review.settings.current.diff_layout === layout.value}
							onclick={() => review.settings.change({ diff_layout: layout.value })}
						>
							{layout.label}
						</Segment>
					{/each}
				</Segmented>
			</Setting>

			<Checkbox
				drawn="box"
				checked={review.settings.current.ignore_whitespace}
				testId="ignore-whitespace"
				onToggle={(checked: boolean) => review.setIgnoreWhitespace(checked)}
			>
				Ignore whitespace
			</Checkbox>
		{/if}

		<Setting label="Theme" testId="theme-setting">
			<Segmented label="Theme" testId="theme-toggle">
				{#each themes as choice (choice.value)}
					<Segment
						testId={choice.testId}
						pressed={review.settings.current.theme === choice.value}
						onclick={() => review.settings.change({ theme: choice.value })}
					>
						{choice.label}
					</Segment>
				{/each}
			</Segmented>
		</Setting>

		<Checkbox
			drawn="box"
			note="only in a background tab"
			checked={review.settings.current.sound_on_replies}
			testId="reply-sound"
			onToggle={(checked: boolean) => review.settings.change({ sound_on_replies: checked })}
		>
			Tick on a new reply
		</Checkbox>

		<!-- Drawn in every review, one no story can be told of too: the choice is the reader's, for all of them -->
		<Checkbox
			drawn="box"
			note="Each story spends the agent's tokens"
			checked={review.settings.current.stories}
			testId="stories"
			onToggle={(checked: boolean) => (checked ? review.turnStoriesOn() : review.turnStoriesOff())}
		>
			Stories
		</Checkbox>
	</div>
</Popover>
