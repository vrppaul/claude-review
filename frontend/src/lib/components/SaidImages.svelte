<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import { imageUrl } from '$lib/utils/images';

	interface Props {
		images: string[];
	}

	let { images }: Props = $props();

	// Images that could not be drawn: most often a review restarted since they
	// were sent, but a file the browser cannot decode looks the same from here
	const lost = new SvelteSet<string>();
</script>

<!-- What was sent, each at full size in a tab of its own: the panel and the
	threads are too narrow to read a screenshot in -->
{#if images.length > 0}
	<div class="mt-2 flex flex-wrap gap-2">
		{#each images as imageId (imageId)}
			{#if lost.has(imageId)}
				<span data-testid="lost-image" class="cr-image-thumb cr-image-lost cr-faint">
					can no longer be shown
				</span>
			{:else}
				<a data-testid="said-image" href={imageUrl(imageId)} target="_blank" rel="noopener noreferrer">
					<img
						src={imageUrl(imageId)}
						alt="Sent with this message"
						class="cr-image-thumb"
						loading="lazy"
						onerror={() => lost.add(imageId)}
					/>
				</a>
			{/if}
		{/each}
	</div>
{/if}
