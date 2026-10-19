<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import { imageUrl } from '$lib/api/review-api';
	import Thumbnail from '$lib/ui/Thumbnail.svelte';

	// What stands where an image was that the review no longer has
	const NO_LONGER_SHOWN = 'can no longer be shown';

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
				<Thumbnail shows="lost" said={NO_LONGER_SHOWN} testId="lost-image" />
			{:else}
				<Thumbnail
					shows="image"
					src={imageUrl(imageId)}
					alt="Sent with this message"
					onLost={() => lost.add(imageId)}
					opens={{ href: imageUrl(imageId), testId: 'said-image' }}
					testId="said-image-picture"
				/>
			{/if}
		{/each}
	</div>
{/if}
