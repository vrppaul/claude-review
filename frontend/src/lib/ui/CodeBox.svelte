<script lang="ts">
	import { CARD_TONES } from './card';

	interface Props {
		/** The code as it is written, its lines broken where it breaks them. */
		code: string;
		testId: string;
	}

	let { code, testId }: Props = $props();
</script>

<!-- Code set apart to read or copy as written: on a quiet card, in the code's face and size, a line wider than
	the box scrolling inside it -->
<pre data-testid={testId} class={['cr-ui-card cr-ui-code-box', CARD_TONES.quiet]}>{code}</pre>
