<script lang="ts">
	/** What the lines are: code, read in the code's face as written, or prose, read as words. */
	type QuoteReads = 'code' | 'prose';

	interface Props {
		/** What the figure says it is: "Written against". */
		caption: string;
		lines: readonly string[];
		reads: QuoteReads;
		testId: string;
	}

	let { caption, lines, reads, testId }: Props = $props();
</script>

<!-- A copy kept of what something was written on, once it is no longer there: a figure on the reading ground,
	edged as a pane, its caption ruled off above its lines, all of it quieter than what is said under it -->
<figure data-testid={testId} class="cr-ui-kept-quote">
	<figcaption>{caption}</figcaption>
	{#if reads === 'code'}
		<pre class="cr-ui-kept-quote-code">{lines.join('\n')}</pre>
	{:else}
		<div class="cr-ui-kept-quote-words">
			{#each lines as line, position (position)}
				<p>{line}</p>
			{/each}
		</div>
	{/if}
</figure>
