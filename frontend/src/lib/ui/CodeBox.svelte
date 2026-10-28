<script lang="ts">
	import { CARD_TONES } from './card';

	interface Props {
		/** The code as it is written, its lines broken where it breaks them. */
		code: string;
		/**
		 * Whether it is read to the letter rather than as code: its lines broken again where the box ends, so no word
		 * hides past its edge, in plain ink, as what matters most where it stands — the issue a reader's feedback opens.
		 */
		wrapped?: boolean;
		testId: string;
	}

	let { code, wrapped = false, testId }: Props = $props();
</script>

<!-- Code set apart to read or copy as written: on a quiet card, in the code's face and size, a line wider than
	the box scrolling inside it, or broken where the box ends -->
<pre
	data-testid={testId}
	class={['cr-ui-card cr-ui-code-box', CARD_TONES.quiet, wrapped && 'cr-ui-code-box-wrapped']}>{code}</pre>
