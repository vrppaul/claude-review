<script lang="ts">
	import type { ReviewPage } from '$lib/page/review-page.svelte';
	import ReviewScreen from '$lib/components/ReviewScreen.svelte';

	interface Props {
		page: ReviewPage;
	}

	let { page }: Props = $props();
</script>

{#if page.state.kind === 'opening'}
	<div class="flex items-center justify-center min-h-screen">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if page.state.kind === 'failed'}
	<div class="flex items-center justify-center min-h-screen">
		<div class="alert alert-error max-w-(--cr-failure-width)">
			<span>{page.state.reason}</span>
		</div>
	</div>
{:else}
	<ReviewScreen review={page.state.review} />
{/if}
