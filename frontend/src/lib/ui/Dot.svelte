<script lang="ts">
	import { DOT_TONES, type DotTone } from './dot';

	interface Props {
		tone: DotTone;
		/** Whether it breathes, while what it marks is on its way. */
		breathing?: boolean;
		testId: string;
	}

	let { tone, breathing = false, testId }: Props = $props();
</script>

<!-- A mark for the eye, in the colour of its tone (lib/ui/dot.ts): the words beside it say what it marks -->
<span aria-hidden="true" data-testid={testId} class={['cr-ui-dot', DOT_TONES[tone], breathing && 'cr-ui-dot-breathing']}
></span>
