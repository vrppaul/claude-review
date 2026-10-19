<script lang="ts">
	import type { DotTone } from './dot';
	import Dot from './Dot.svelte';

	interface Props {
		/**
		 * The colour they breathe in: quietly beside words that say what is waited on, in the agent's colour while
		 * the agent writes, in the colour of what they stand in on a button's fill.
		 */
		tone: DotTone;
		/** Their test id; each dot is known by it followed by `-dot`. */
		testId: string;
	}

	let { tone, testId }: Props = $props();
</script>

<!-- Something on its way — an answer, a story being written, a review being sent or opened, an image uploading —
	as three dots that breathe in turn: a line that never changes reads as a hang. Unsaid to a screen reader, as
	every dot is: the words beside them say what is waited on -->
<span data-testid={testId} class="cr-ui-breathing-dots">
	<Dot {tone} breathing testId="{testId}-dot" />
	<Dot {tone} breathing testId="{testId}-dot" />
	<Dot {tone} breathing testId="{testId}-dot" />
</span>
