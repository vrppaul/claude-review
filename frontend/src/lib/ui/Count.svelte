<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';

	/**
	 * Whose the figure is, which sets its colour; where it stands sets the rest (ui.css): in a filled button
	 * it is reversed on the fill, in a control pressed or open on the control's words
	 * - reader: how many of the reader's threads, or of their comments, on the control's fill
	 * - unread: how many of the agent's answers wait unread, in the colour of what is unread
	 */
	type CountTone = 'reader' | 'unread';

	// The class of each in the library's stylesheet, over the one every count has
	const TONES: Record<CountTone, string | null> = { reader: null, unread: 'cr-ui-count-unread' };

	/**
	 * Besides these, what lands on the figure: its words under the pointer (`title`), kept from a screen reader
	 * where the name of what it stands in says how many in words (`aria-hidden`), the tour's name for it.
	 */
	interface Props extends Omit<HTMLAttributes<HTMLSpanElement>, 'class' | 'style' | 'children'> {
		tone: CountTone;
		count: number;
		testId: string;
	}

	let { tone, count, testId, ...attributes }: Props = $props();
</script>

<!-- How many there are of what it stands beside, or goes with, on their mark, in a tag's box (lib/ui/tag.ts): its
	test id and look the library's alone, written after what it is handed -->
<span {...attributes} data-testid={testId} class={['cr-ui-count', TONES[tone]]}>{count}</span>
