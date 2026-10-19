<script lang="ts">
	import type { ReviewPage } from '$lib/page/review-page.svelte';
	import ReviewScreen from '$lib/components/ReviewScreen.svelte';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Failure from '$lib/ui/Failure.svelte';

	interface Props {
		page: ReviewPage;
	}

	let { page }: Props = $props();
</script>

{#if page.state.kind === 'opening'}
	<div class="flex items-center justify-center min-h-screen">
		<BreathingDots tone="quiet" testId="opening-dots" />
	</div>
{:else if page.state.kind === 'failed'}
	<div class="flex items-center justify-center min-h-screen">
		<div class="max-w-(--cr-failure-width)">
			<Failure stands="apart" testId="opening-failed" said={page.state.reason} />
		</div>
	</div>
{:else}
	<ReviewScreen review={page.state.review} />
{/if}
