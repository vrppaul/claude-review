<script lang="ts">
	import { REPOSITORY, REPOSITORY_URL } from '$lib/guide/repository';
	import Actions from '$lib/ui/Actions.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Link from '$lib/ui/Link.svelte';
	import LinkButton from '$lib/ui/LinkButton.svelte';

	interface Props {
		/** What following the repository or Star does to what the ask stands in: Help puts itself away. */
		onfollow: () => void;
	}

	// Why the reader is asked, beside the act; and the star the act adds, where GitHub's Star button keeps its count
	const WHY = 'Your star helps other Claude Code users find it.';
	const ONE_MORE = '+1';

	let { onfollow }: Props = $props();
</script>

<!-- The ask for a star, at a pane's foot: the repository by name on GitHub's mark, a link to it, and under it why,
	beside GitHub's own Star button, which adds the reader's star -->
<div data-testid="star-on-github-ask" class="flex flex-col gap-1.5 p-3">
	<Heading tag="p" heads="pane">
		<span class="flex items-center gap-2">
			<Icon name="github" size="base" />
			<Link href={REPOSITORY_URL} {onfollow} testId="star-repository">{REPOSITORY}</Link>
		</span>
	</Heading>
	<Actions testId="star-on-github-actions" asideWraps>
		{#snippet aside()}
			<p class="cr-muted text-xs">{WHY}</p>
		{/snippet}
		{#snippet main()}
			<LinkButton tone="primary" size="sm" href={REPOSITORY_URL} adds={ONE_MORE} {onfollow} testId="star-on-github">
				<Icon name="star" size="sm" />
				Star
			</LinkButton>
		{/snippet}
	</Actions>
</div>
