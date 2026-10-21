<script lang="ts">
	import { useReview } from '$lib/review/context';
	import type { Checkout, ReviewMode } from '$lib/types';
	import Icon from '$lib/ui/Icon.svelte';
	import type { IconName } from '$lib/ui/icons';

	// What a review of no repository is marked by, beside what it is called: the files read, the conversation
	const MARK_OF: Record<ReviewMode, IconName> = { diff: 'compare', files: 'files', transcript: 'conversation' };
	// What is checked out, by its mark and in the words the pointer says it in round its name, after the
	// repository's: "claude-review, at the commit a1b2c3d, on no branch"
	const CHECKED_OUT: Record<Checkout['at'], { mark: IconName; said: string; after: string }> = {
		branch: { mark: 'branch', said: 'on the branch', after: '' },
		commit: { mark: 'commit', said: 'at the commit', after: ', on no branch' }
	};

	const review = useReview();

	/** What is checked out, by its name: the branch's, or the commit's short id. */
	function nameOf(checkout: Checkout): string {
		switch (checkout.at) {
			case 'branch':
				return checkout.branch;
			case 'commit':
				return checkout.commit;
		}
	}
</script>

<!-- Where the change is, in place of the tool's name: the repository over what it had checked out, two small
	lines in a control's height, giving up room to the controls beside it, each line cut short inside it and whole
	on the pointer; the branch runs no further than --cr-branch-widest, and gives way in a narrow window. A review of
	no repository: its mark and what it is called, on one line -->
{#if review.repository}
	{@const checkedOut = CHECKED_OUT[review.repository.checkout.at]}
	{@const name = nameOf(review.repository.checkout)}
	<span
		data-testid="where-the-change-is"
		class="flex min-w-0 flex-col"
		title="{review.repository.name}, {checkedOut.said} {name}{checkedOut.after}"
	>
		<!-- Each line as wide as the block, so it is cut inside it however far the block gives way -->
		<span data-testid="where-line" class="truncate text-xs font-semibold">{review.repository.name}</span>
		<span
			data-testid="where-line"
			class="cr-muted flex max-w-(--cr-branch-widest) min-w-0 items-center gap-1 max-cr-header-repository:sr-only"
		>
			<Icon name={checkedOut.mark} size="xs" />
			<span class="truncate font-mono text-2xs">{name}</span>
		</span>
	</span>
{:else if review.title}
	<span data-testid="where-the-change-is" class="flex min-w-0 items-center gap-1.5" title={review.title}>
		<span class="cr-muted flex"><Icon name={MARK_OF[review.mode]} size="xs" /></span>
		<span data-testid="where-line" class="truncate text-xs font-semibold">{review.title}</span>
	</span>
{/if}
