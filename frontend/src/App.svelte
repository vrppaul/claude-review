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
{:else if page.state.kind === 'elsewhere'}
	<div class="flex items-center justify-center min-h-screen">
		<div data-testid="open-elsewhere" class="alert max-w-md">
			<span>This review is open in another tab. It opens here once that tab is closed.</span>
		</div>
	</div>
{:else if page.state.kind === 'failed'}
	<div class="flex items-center justify-center min-h-screen">
		<div class="alert alert-error max-w-md">
			<span>{page.state.reason}</span>
		</div>
	</div>
{:else}
	<ReviewScreen review={page.state.review} />
{/if}
