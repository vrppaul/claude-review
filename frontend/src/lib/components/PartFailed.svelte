<script lang="ts">
	import Button from '$lib/ui/Button.svelte';
	import { messageOf } from '$lib/utils/errors';
	import Icon from './Icon.svelte';

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
<div
	data-testid="part-failed"
	role="alert"
	class="cr-notice cr-notice-broken flex items-center gap-3 border-b border-base-300 px-4 py-2 text-xs"
>
	<Icon name="notice" class="h-3 w-3 shrink-0" />
	<span class="min-w-0 flex-1">
		{what} could not be drawn: {messageOf(error)}. The rest of the review still works.
	</span>
	<Button tone="quiet" size="xs" testId="redraw-part" onclick={retry}>Try again</Button>
</div>
