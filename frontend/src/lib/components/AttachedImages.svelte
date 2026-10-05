<script lang="ts">
	import type { ImageAttachments } from '$lib/utils/image-attachments.svelte';
	import { imageUrl } from '$lib/utils/images';

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
			<span class="cr-image-attached">
				<img
					data-testid="attached-image"
					src={imageUrl(imageId)}
					alt="Attached to what is being written"
					class="cr-image-thumb"
					onerror={() => onLost(imageId)}
				/>
				<button
					data-testid="detach-image"
					class="cr-image-detach rounded-full"
					aria-label="Remove this image"
					{disabled}
					onclick={() => attachments.detach(imageId)}>×</button
				>
			</span>
		{/each}
		{#if attachments.uploading > 0}
			<span data-testid="image-uploading" class="cr-image-thumb cr-image-pending">
				<span class="loading loading-xs loading-spinner"></span>
			</span>
		{/if}
	</div>
{/if}
