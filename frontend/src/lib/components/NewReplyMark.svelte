<script lang="ts">
	import Dot from '$lib/ui/Dot.svelte';
</script>

<!-- An answer in a thread nobody has looked at yet; the dot is for the eye, the words for everyone -->
<span data-testid="comment-unread" class="inline-flex shrink-0 items-center gap-1 text-xs text-(--cr-unread)">
	<Dot tone="unread" testId="comment-unread-dot" /> new reply
</span>
