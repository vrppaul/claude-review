<script lang="ts">
	import type { Thread } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();

	/** Take the thread up again; the button goes with its settling, and the keyboard stays with the thread. */
	function reopen() {
		review.threads.setResolved(thread.id, false);
		review.sections.keyboardToThread(thread.id);
	}
</script>

<!-- Taking a settled thread up again, from its folded line or the head of its first turn alike -->
<Button tone="secondary" size="xs" data-testid="reopen-thread" onclick={reopen}>Reopen</Button>
