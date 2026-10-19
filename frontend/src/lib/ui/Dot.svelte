<script lang="ts">
	import { DOT_TONES, type DotTone } from './dot';

	interface Props {
		tone: DotTone;
		/** Whether it breathes, while what it marks is on its way. */
		breathing?: boolean;
		/** What it marks, shown under the pointer, where the words that say it are kept for a screen reader alone. */
		title?: string | undefined;
		testId: string;
	}

	let { tone, breathing = false, title, testId }: Props = $props();
</script>

<!-- A mark for the eye, in the colour of its tone (lib/ui/dot.ts): the words beside it say what it marks -->
<span
	aria-hidden="true"
	data-testid={testId}
	{title}
	class={['cr-ui-dot', DOT_TONES[tone], breathing && 'cr-ui-dot-breathing']}
></span>
