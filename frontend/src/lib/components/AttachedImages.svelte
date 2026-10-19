<script lang="ts">
	import type { ImageAttachments } from '$lib/review/image-attachments.svelte';
	import { imageUrl } from '$lib/api/review-api';
	import Thumbnail from '$lib/ui/Thumbnail.svelte';

	interface Props {
		attachments: ImageAttachments;
		/** Shut while sending: the images are already on their way. */
		disabled?: boolean;
		/** An image that cannot be drawn, taken off by the caller with a note. */
		onLost: (imageId: string) => void;
	}

	let { attachments, disabled = false, onLost }: Props = $props();
</script>

<!-- What is pasted under a field, before it is sent -->
{#if attachments.images.length > 0 || attachments.uploading > 0}
	<div data-testid="attached-images" class="mb-2 flex flex-wrap gap-2">
		{#each attachments.images as imageId (imageId)}
			<Thumbnail
				shows="image"
				src={imageUrl(imageId)}
				alt="Attached to what is being written"
				onLost={() => onLost(imageId)}
				removing={{
					label: 'Remove this image',
					disabled,
					onRemove: () => attachments.detach(imageId),
					testId: 'detach-image'
				}}
				testId="attached-image"
			/>
		{/each}
		{#if attachments.uploading > 0}
			<Thumbnail shows="uploading" testId="image-uploading" />
		{/if}
	</div>
{/if}
