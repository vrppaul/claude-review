<script lang="ts">
	import { lendKeyboardToWhatRemains } from '$lib/dom/keyboard';
	import { REPOSITORY, REPOSITORY_URL } from '$lib/guide/repository';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Link from '$lib/ui/Link.svelte';
	import LinkButton from '$lib/ui/LinkButton.svelte';

	// Why the reader is asked, beside the act; the star the act adds, where GitHub's Star button keeps its count; and
	// the thanks that stand in the ask's place once the reader went to star it
	const WHY = 'Your star helps other Claude Code users find it.';
	const ONE_MORE = '+1';
	const THANKS = 'Thank you!';
	const THANKS_SAID = 'Every star helps other Claude Code users find claude-review.';

	// Whether the reader went to GitHub by Star. It lasts as long as the pane it stands in, so the next time Help
	// opens it asks again: whether they starred it there, the page cannot know
	let thanked = $state(false);
	let thanks: HTMLElement | undefined = $state();

	/** The reader went to star it: the thanks stand in the ask's place, and take the keyboard Star held. */
	function thank() {
		thanked = true;
		lendKeyboardToWhatRemains(() => thanks);
	}
</script>

<!-- The ask for a star, at a pane's foot: the repository by name on GitHub's mark, a link to it, and under it why,
	beside a Star button drawn as GitHub draws its own, which adds the reader's star. Once they follow it, thanks with
	a heart in its place, said to a screen reader as they come -->
{#if thanked}
	<div bind:this={thanks} data-testid="star-on-github-thanks" role="status" class="flex items-center gap-3 p-3">
		<Icon name="heart" size="xl" tone="reader" />
		<div class="flex min-w-0 flex-col gap-0.5">
			<Heading tag="p" heads="pane">{THANKS}</Heading>
			<p class="cr-muted text-xs">{THANKS_SAID}</p>
		</div>
	</div>
{:else}
	<div data-testid="star-on-github-ask" class="flex flex-col gap-1.5 p-3">
		<Heading tag="p" heads="pane">
			<span class="flex items-center gap-2">
				<Icon name="github" size="base" />
				<Link href={REPOSITORY_URL} testId="star-repository">{REPOSITORY}</Link>
			</span>
		</Heading>
		<!-- Why at the left, wrapping as the pane narrows, and GitHub's button at the right, kept whole: no act that
			ends the pane, which a row of acts (Actions) would lead with a primary one -->
		<div class="flex items-center gap-2">
			<p class="cr-muted min-w-0 flex-1 text-xs">{WHY}</p>
			<LinkButton
				tone="secondary"
				size="sm"
				href={REPOSITORY_URL}
				adds={ONE_MORE}
				onfollow={thank}
				testId="star-on-github"
			>
				<Icon name="star" size="sm" />
				Star
			</LinkButton>
		</div>
	</div>
{/if}
