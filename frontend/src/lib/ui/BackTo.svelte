<script lang="ts">
	import Button from './Button.svelte';
	import Icon from './Icon.svelte';

	interface Props {
		/** Where it leads, as short as the reader knows it: a file's name and a line, `routes.ts:33`. */
		place: string;
		/** Where it leads in full, on the pointer: `src/http/routes.ts:33`. */
		whole: string;
		testId: string;
		onclick: () => void;
	}

	let { place, whole, testId, onclick }: Props = $props();
</script>

<!-- The way back to where the reader was before the page took them elsewhere, across the room it stands in: Back to,
	then the place in the code's face, cut with an ellipsis where the room ends, and whole on the pointer -->
<Button tone="secondary" size="sm" listed {testId} title="Back to {whole}" {onclick}>
	<Icon name="chevron" size="xs" pointing="left" />
	<span class="cr-ui-back-to">Back to <span class="cr-ui-back-to-place">{place}</span></span>
</Button>
