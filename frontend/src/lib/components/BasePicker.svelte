<script lang="ts">
	import type { ReviewVersion, VersionKind } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import { messageOf } from '$lib/utils/errors';
	import { timeAgo } from '$lib/utils/time';
	import { counted, FILES } from '$lib/utils/words';
	import Icon from './Icon.svelte';
	import Popover from './Popover.svelte';

	const review = useReview();

	let open = $state(false);
	let filter = $state('');
	let failed = $state<string | null>(null);
	let asking = $state(false);

	const sections: { kind: VersionKind; title: string }[] = [
		{ kind: 'review', title: 'This review' },
		{ kind: 'round', title: 'Rounds' },
		{ kind: 'ref', title: 'Branches and tags' }
	];

	const matching = $derived(
		review.diff.versions.filter((version) => version.label.toLowerCase().includes(filter.trim().toLowerCase()))
	);
	const hasRounds = $derived(review.diff.versions.some((version) => version.kind === 'round'));

	/** Open or close the list; opened, it asks git afresh what there is to compare against. */
	function setOpen(next: boolean) {
		open = next;
		if (next) void listBases();
	}

	async function listBases() {
		filter = '';
		failed = null;
		asking = true;
		try {
			await review.diff.loadVersions();
		} catch (error) {
			failed = messageOf(error);
		} finally {
			asking = false;
		}
	}

	async function pick(version: ReviewVersion) {
		failed = null;
		try {
			await review.diff.setBase(version.key);
			open = false;
		} catch (error) {
			failed = messageOf(error);
		}
	}

	/** What a row says about a base on its right: its size, or its age. */
	function meta(version: ReviewVersion): string {
		if (version.changed !== null) return counted(version.changed, FILES);
		return version.at === null ? '' : timeAgo(version.at, review.clock.now);
	}
</script>

<!-- The second half of the title, made a control: the header still reads
	as one sentence, and takes the mark tint while a narrower base is on. -->
<Popover
	bind:open={() => open, setOpen}
	label="Compare the working tree against"
	placement="below-start"
	data-testid="base-list"
	data-tour="review-base-list"
	class="w-80"
>
	{#snippet trigger(control)}
		<Button
			{...control}
			tone={review.diff.narrowed ? 'marked' : 'quiet'}
			size="xs"
			testId="base-picker"
			data-tour="review-base"
			title="What the working tree is compared against"
		>
			<Icon name="compare" class="h-3 w-3 shrink-0" />
			<!-- What it is read against, named as the bases listed are: in the code's face -->
			<span data-testid="base-named" class="font-mono">{review.diff.phrase}</span>
			<Icon name="chevron" class="h-3 w-3 shrink-0" />
		</Button>
	{/snippet}

	<div class="px-3 pt-2 pb-1">
		<p class="cr-muted text-xs">Compare the working tree against</p>
		<input
			data-testid="base-filter"
			class="mt-2 w-full rounded border border-base-300 bg-base-100 px-2 py-1 font-mono text-xs"
			placeholder="filter"
			aria-label="Filter the bases"
			bind:value={filter}
		/>
	</div>

	{#each sections as section (section.kind)}
		{@const listed = matching.filter((version) => version.kind === section.kind)}
		{#if listed.length > 0}
			<p class="cr-faint px-3 pt-2 pb-1 text-xs">{section.title}</p>
			{#each listed as version (version.key)}
				{@const inForce = version.key === review.diff.base}
				<button
					type="button"
					data-testid="base-option"
					class={['cr-pressable flex w-full items-center gap-2 px-3 py-1.5 text-left', inForce && 'cr-current']}
					onclick={() => pick(version)}
				>
					<span class="w-3 shrink-0">
						{#if inForce}
							<Icon name="check" class="h-3 w-3 text-(--cr-control)" label="In force" />
						{/if}
					</span>
					<span class="flex-1 truncate font-mono text-xs">{version.label}</span>
					<span class="cr-faint shrink-0 text-xs">{meta(version)}</span>
				</button>
			{/each}
		{/if}
	{/each}

	{#if asking && matching.length === 0}
		<p data-testid="bases-asking" class="cr-muted px-3 py-6 text-center text-xs">
			Asking git what this can be read against…
		</p>
	{:else if matching.length === 0 && !failed}
		<p data-testid="no-bases" class="cr-muted px-3 py-6 text-center text-xs">
			{filter.trim() ? 'Nothing here answers to that.' : 'Nothing to compare against.'}
		</p>
	{/if}

	{#if failed}
		<p data-testid="base-error" class="border-t border-base-300 px-3 py-2 text-xs text-error">
			{failed}
		</p>
	{/if}

	{#if hasRounds}
		<p class="cr-faint border-t border-base-300 px-3 py-2 text-xs">
			Rounds are kept for as long as this review is open.
		</p>
	{/if}
</Popover>
