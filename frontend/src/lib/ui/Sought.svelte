<script lang="ts" module>
	/** A stretch of words by its characters, the end left out. */
	interface Stretch {
		start: number;
		end: number;
	}

	/** Where what was asked for first stands in words, whatever its case, as the filter matches; none where it does not. */
	function firstStretch(words: string, sought: string): Stretch | null {
		if (sought === '') return null;
		const start = words.toLowerCase().indexOf(sought.toLowerCase());
		return start < 0 ? null : { start, end: start + sought.length };
	}
</script>

<script lang="ts">
	import { SOUGHT_MARK } from './sought';

	interface Props {
		/** The words drawn: a name as the code writes it. */
		words: string;
		/** What the reader typed to find them, lit where it first stands in them; nothing lit while it is empty. */
		sought: string;
		testId: string;
	}

	let { words, sought, testId }: Props = $props();

	const lit = $derived(firstStretch(words, sought));
</script>

<!-- Words with what the reader asked for lit where it stands in them, in the look it has on a line of the code -->
{#if lit === null}{words}{:else}{words.slice(0, lit.start)}<span data-testid={testId} class={SOUGHT_MARK}
		>{words.slice(lit.start, lit.end)}</span
	>{words.slice(lit.end)}{/if}
