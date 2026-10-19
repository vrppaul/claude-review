<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import NoticeBar from '$lib/ui/NoticeBar.svelte';
	import { messageOf } from '$lib/utils/errors';

	interface Props {
		/** What could not be drawn, as the reader knows it: a file's path, the panel. */
		what: string;
		/** What broke it. */
		error: unknown;
		/** Draw it again. */
		retry: () => void;
	}

	let { what, error, retry }: Props = $props();
</script>

<!-- In place of a part that could not be drawn: what it was, why, and that the rest still works -->
<NoticeBar tone="warning" icon="notice" testId="part-failed" role="alert">
	{what} could not be drawn: {messageOf(error)}. The rest of the review still works.
	{#snippet actions()}
		<Button tone="quiet" size="xs" testId="redraw-part" onclick={retry}>Try again</Button>
	{/snippet}
</NoticeBar>
