<script lang="ts">
	import type { Thread } from '$lib/types';
	import { useReview } from '$lib/review/context';

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

<!-- Taking a settled thread up again, from its folded line or its open heading alike -->
<button type="button" data-testid="reopen-thread" class="btn btn-ghost btn-xs" onclick={reopen}> Reopen </button>
