<script lang="ts">
	import { suggestedChange, type SuggestedLine } from '$lib/utils/suggestion';

	// How each line is drawn by what the suggestion does to it, in the diff's own signs and colours
	const SIGNS: Record<SuggestedLine['change'], string> = { kept: ' ', removed: '−', added: '+' };
	const ROWS: Record<SuggestedLine['change'], string> = { kept: '', removed: 'cr-sugg-del', added: 'cr-sugg-add' };

	interface Props {
		/** The lines the suggestion replaces: those the comment was written on. */
		replaced: string[];
		/** What it puts there, a line to each line of text. */
		suggested: string;
	}

	let { replaced, suggested }: Props = $props();

	const lines = $derived(suggestedChange(replaced, suggested));
</script>

<!-- A suggestion is a change, so it is shown as one: what it takes away
	and what it puts there, marked the way the diff marks them, between the
	lines it keeps. Spans, so it can stand inside a row that is a button. -->
<span data-testid="comment-suggestion" class="cr-suggestion mt-2">
	{#each lines as line, index (index)}
		<span data-testid="suggestion-line" class={['cr-sugg-row', ROWS[line.change]]}
			><span class="cr-sugg-sign">{SIGNS[line.change]}</span>{line.text}</span
		>
	{/each}
</span>
