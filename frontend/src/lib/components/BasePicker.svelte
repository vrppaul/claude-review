<script lang="ts">
	import type { ReviewVersion, VersionKind } from '$lib/types';
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Button from '$lib/ui/Button.svelte';
	import EmptyNote from '$lib/ui/EmptyNote.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import Filter from '$lib/ui/Filter.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Popover from '$lib/ui/Popover.svelte';
	import Row from '$lib/ui/Row.svelte';
	import { messageOf } from '$lib/utils/errors';
	import { timeAgo } from '$lib/utils/time';
	import { counted, FILES } from '$lib/utils/words';

	// What the list is called, and headed with
	const COMPARED_AGAINST = 'Compare the working tree against';

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
	label={COMPARED_AGAINST}
	heading={COMPARED_AGAINST}
	placement="below-start"
	width="medium"
	testId="base-list"
	data-tour={tourStop('review-base-list')}
>
	{#snippet trigger(control)}
		<Button
			{...control}
			tone={review.diff.narrowed ? 'marked' : 'quiet'}
			size="sm"
			testId="base-picker"
			data-tour={tourStop('review-base')}
			title="What the working tree is compared against"
		>
			<Icon name="compare" size="xs" />
			<!-- What it is read against, named as the bases listed are: in the code's face, given way to its mark and
				its arrow as the window narrows, as the board draws it, and still said to a screen reader -->
			<span data-testid="base-named" class="font-mono max-cr-header-narrower:sr-only">{review.diff.phrase}</span>
			<Icon name="chevron" size="xs" />
		</Button>
	{/snippet}

	<div class="px-3 pt-2 pb-1">
		<Filter bind:value={filter} label="Filter the bases" testId="base-filter" placeholder="filter" />
	</div>

	<!-- Each base a row on the filter field's edges, a section's name as far in as a row's words -->
	<div class="px-3 pb-1">
		{#each sections as section (section.kind)}
			{@const listed = matching.filter((version) => version.kind === section.kind)}
			{#if listed.length > 0}
				<p class="cr-faint px-(--cr-list-row-room) pt-2 pb-1 text-xs">{section.title}</p>
				{#each listed as version (version.key)}
					{@const inForce = version.key === review.diff.base}
					<Row names="path" testId="base-option" current={inForce} onclick={() => pick(version)}>
						{#snippet leading()}
							<!-- Room for the check of the one in force in every row, so their names stand in one line -->
							<span class="w-(--cr-list-row-mark-slot)">
								{#if inForce}
									<Icon name="check" size="xs" tone="reader" label="In force" />
								{/if}
							</span>
						{/snippet}
						{#snippet label()}
							{version.label}
						{/snippet}
						{#snippet trailing()}
							<span class="cr-faint">{meta(version)}</span>
						{/snippet}
					</Row>
				{/each}
			{/if}
		{/each}
	</div>

	{#if asking && matching.length === 0}
		<EmptyNote within="list" testId="bases-asking">
			<BreathingDots tone="quiet" testId="bases-asking-dots" />
			Asking git what this can be read against
		</EmptyNote>
	{:else if matching.length === 0 && !failed}
		<EmptyNote within="list" testId="no-bases">
			{filter.trim() ? 'Nothing here answers to that.' : 'Nothing to compare against.'}
		</EmptyNote>
	{/if}

	{#if failed}
		<div data-testid="base-error-room" class="border-t border-base-300 px-3 py-2">
			<Failure stands="apart" testId="base-error" said={failed} />
		</div>
	{/if}

	{#if hasRounds}
		<p class="cr-faint border-t border-base-300 px-3 py-2 text-xs">
			Rounds are kept for as long as this review is open.
		</p>
	{/if}
</Popover>
