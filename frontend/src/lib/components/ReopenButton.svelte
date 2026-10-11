<script lang="ts">
	import type { Thread } from '$lib/types';
	import { useReview } from '$lib/review/context';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();
</script>

<!-- Taking a settled thread up again, from its folded line or its open heading alike -->
<button
	type="button"
	data-testid="reopen-thread"
	class="btn btn-ghost btn-xs"
	onclick={() => review.threads.setResolved(thread.id, false)}
>
	Reopen
</button>
