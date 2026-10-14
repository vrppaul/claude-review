<script lang="ts">
	import type { StoryAnchor } from '$lib/types';
	import { anchorLabel } from '$lib/anchors/views';

	interface Props {
		anchor: StoryAnchor;
	}

	let { anchor }: Props = $props();
</script>

<!-- The block of the story's words the thread hangs on, by what the story heads it with, as quietly as the
	head it is said in says the rest -->
<span data-testid="comment-block-label">{anchorLabel(anchor)}</span>
