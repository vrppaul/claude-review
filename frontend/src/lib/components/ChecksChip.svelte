<script lang="ts" module>
	import type { Check } from '$lib/types';
	import type { ButtonTone } from '$lib/ui/button';
	import type { IconName } from '$lib/ui/icons';
	import { wordsFor, type CountedWords } from '$lib/utils/words';

	/** The worst of what the checks say, as the chip says it: its look, its mark, a figure and the words after it. */
	interface ChipSays {
		tone: ButtonTone;
		icon: IconName;
		figure: number;
		words: string;
	}

	const CHECKS: CountedWords = { one: 'check', many: 'checks' };
	// The checks the code changed after, as the sentence over them names them
	const THESE: CountedWords = { one: 'this', many: 'these' };

	/** A failure on the code on screen first, then what the code changed after, then that every one passed. */
	function worstOf(total: number, failing: number, outOfDate: number): ChipSays {
		if (failing > 0) return { tone: 'failing', icon: 'cross', figure: failing, words: `of ${total} failed` };
		if (outOfDate > 0) return { tone: 'warned', icon: 'old', figure: outOfDate, words: `of ${total} out of date` };
		return { tone: 'quiet', icon: 'check', figure: total, words: wordsFor(total, CHECKS) };
	}

	/** Whether a check failed on the code on screen. */
	function failsNow(check: Check): boolean {
		return check.status === 'failed' && !check.out_of_date;
	}
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import CheckFailure from '$lib/ui/CheckFailure.svelte';
	import CheckList from '$lib/ui/CheckList.svelte';
	import CheckRow from '$lib/ui/CheckRow.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import OutOfDateChecks from '$lib/ui/OutOfDateChecks.svelte';
	import Popover from '$lib/ui/Popover.svelte';
	import { fileName } from '$lib/utils/paths';
	import { clockTime } from '$lib/utils/time';
	import FileChip from './FileChip.svelte';

	// What the pane is called and headed with, and what stands beside its heading: whose word the checks are
	const HEADING = 'Checks';
	const WHOSE = 'as the agent reported them';
	// What heads the sentence over the checks the code changed after
	const OUT_OF_DATE = 'Out of date.';

	const review = useReview();

	let open = $state(false);

	const checks = $derived(review.checks.all);
	// Failed first, then those the code changed after, then the rest: the order of what the reader must look at
	const failing = $derived(checks.filter(failsNow));
	const outOfDate = $derived(checks.filter((check) => check.out_of_date));
	const standing = $derived(checks.filter((check) => !check.out_of_date && !failsNow(check)));
	const says = $derived(worstOf(checks.length, failing.length, outOfDate.length));
	const named = $derived(`${HEADING}: ${says.figure} ${says.words}`);
	// Every file that changed after one of them ran, once; none where git could not say
	const changed = $derived([...new Set(outOfDate.flatMap((check) => check.changed_since ?? []))]);
	const ranBefore = $derived(wordsFor(outOfDate.length, THESE));
	const outOfDateSaid = $derived(
		changed.length > 0
			? `The code changed after ${ranBefore} ran:`
			: `The code may have changed after ${ranBefore} ran.`
	);

	/** Take the reader to the line of a file where a check failed, the pane put away. */
	function goTo(path: string, line: number) {
		open = false;
		void review.navigator.goToLine(path, line);
	}

	/** When a check was reported: the round too, where it is not the one being written. */
	function reportedWhen(check: Check): string {
		const time = clockTime(check.at);
		return check.round === review.rounds.current ? time : `round ${check.round}, ${time}`;
	}
</script>

{#snippet aside()}
	<span class="cr-faint text-xs">{WHOSE}</span>
{/snippet}

<!-- A check, and where it failed under it where that is said of the code on screen -->
{#snippet row(check: Check, failures: Snippet | undefined)}
	<CheckRow
		ended={check.status}
		name={check.name}
		said={check.summary}
		when={reportedWhen(check)}
		outOfDate={check.out_of_date}
		testId="check"
		{failures}
	/>
{/snippet}

{#snippet changedFiles()}
	{#each changed as path (path)}
		<FileChip {path} testId="check-changed-file" />
	{/each}
{/snippet}

<!-- Nothing reported, nothing said -->
{#if checks.length > 0}
	<Popover
		bind:open
		label={HEADING}
		heading={HEADING}
		{aside}
		placement="below-start"
		width="wide"
		testId="checks-pane"
	>
		{#snippet trigger(control)}
			<!-- As the window narrows its words give way, then its figure, the mark kept to the last -->
			<Button {...control} tone={says.tone} size="sm" testId="checks" aria-label={named} title={named}>
				<Icon name={says.icon} size="xs" tone={says.tone === 'quiet' && !open ? 'done' : undefined} />
				<span class="max-cr-header-narrowest:sr-only">
					{says.figure} <span class="max-cr-header-narrower:sr-only">{says.words}</span>
				</span>
			</Button>
		{/snippet}

		<CheckList testId="checks-list">
			{#each failing as check (check.name)}
				{#snippet failures()}
					<!-- Known by place: replaced whole with each report, and a tool may say the same of one line twice -->
					{#each check.failures as failure, place (place)}
						<CheckFailure
							what={failure.what}
							where="{fileName(failure.path)}:{failure.line}"
							why={failure.why}
							title="{failure.path}:{failure.line}"
							testId="check-failure"
							onclick={review.diff.holds(failure.path) ? () => goTo(failure.path, failure.line) : undefined}
						/>
					{/each}
				{/snippet}
				{@render row(check, check.failures.length > 0 ? failures : undefined)}
			{/each}
			{#if outOfDate.length > 0}
				<OutOfDateChecks
					lead={OUT_OF_DATE}
					said={outOfDateSaid}
					testId="checks-out-of-date"
					changed={changed.length > 0 ? changedFiles : undefined}
				>
					{#each outOfDate as check (check.name)}
						{@render row(check, undefined)}
					{/each}
				</OutOfDateChecks>
			{/if}
			{#each standing as check (check.name)}
				{@render row(check, undefined)}
			{/each}
		</CheckList>
	</Popover>
{/if}
