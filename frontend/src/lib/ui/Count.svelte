<script lang="ts">
	/**
	 * Whose the figure is, which sets its colour; where it stands sets the rest (ui.css): in a filled button
	 * it is reversed on the fill, in a control pressed or open on the control's words
	 * - reader: how many of the reader's threads, or of their comments, on the control's fill
	 * - unread: how many of the agent's answers wait unread, in the colour of what is unread
	 */
	type CountTone = 'reader' | 'unread';

	// The class of each in the library's stylesheet, over the one every count has
	const TONES: Record<CountTone, string | null> = { reader: null, unread: 'cr-ui-count-unread' };

	interface Props {
		tone: CountTone;
		count: number;
		/** What the figure counts, in words, under the pointer. */
		title?: string | undefined;
		/** Kept from a screen reader, where the name of what it stands in says how many in words. */
		'aria-hidden'?: boolean | undefined;
		testId: string;
	}

	let { tone, count, title, 'aria-hidden': unsaid, testId }: Props = $props();
</script>

<!-- How many there are of what it stands beside, or goes with, on their mark, in a tag's box (lib/ui/tag.ts) -->
<span aria-hidden={unsaid} data-testid={testId} {title} class={['cr-ui-count', TONES[tone]]}>{count}</span>
