<script lang="ts">
	/**
	 * Where a key stands, which sets how it is drawn:
	 * - inline: among words or on a button, in their line, the colour of the reader's controls
	 * - listed: against what it does in a list of keys (KeyList), drawn as the key itself, in ink
	 */
	type Stands = 'inline' | 'listed';

	// The class of each in the library's stylesheet
	const STANDING: Record<Stands, string | null> = { inline: null, listed: 'cr-ui-key-listed' };

	interface Props {
		/** A key, or keys held together, as the help writes them: `?`, `Ctrl+Enter`. */
		keys: string;
		stands: Stands;
		testId: string;
	}

	let { keys, stands, testId }: Props = $props();
</script>

<!-- A key of the keyboard, as the browser marks one up: in the code's face, what they press, in a box of a line
	round it, as tall as a tag -->
<kbd data-testid={testId} class={['cr-ui-key', STANDING[stands]]}>{keys}</kbd>
