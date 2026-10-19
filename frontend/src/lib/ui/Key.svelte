<script lang="ts">
	interface Props {
		/** A key, or keys held together, as the help writes them: `?`, `Ctrl+Enter`. */
		keys: string;
		testId: string;
	}

	let { keys, testId }: Props = $props();
</script>

<!-- A key of the keyboard, as the browser marks one up: in the code's face and in the colour of the reader's
	controls, what they press, in a box of a line round it, as tall as a tag -->
<kbd data-testid={testId} class="cr-ui-key">{keys}</kbd>
