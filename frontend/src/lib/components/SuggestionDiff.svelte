<script lang="ts">
	interface Props {
		/** The lines the suggestion replaces: those the comment was written on. */
		replaced: string[];
		/** What it puts there, a line to each line of text. */
		suggested: string;
	}

	let { replaced, suggested }: Props = $props();
</script>

<!-- A suggestion is a change, so it is shown as one: the lines it replaces
	above the lines it puts there, marked the way the diff marks them -->
<div data-testid="comment-suggestion" class="cr-suggestion mt-2 overflow-x-auto">
	{#each replaced as line, index (index)}
		<div class="cr-sugg-row cr-sugg-del"><span class="cr-sugg-sign">−</span>{line}</div>
	{/each}
	{#each suggested.split('\n') as line, index (index)}
		<div class="cr-sugg-row cr-sugg-add"><span class="cr-sugg-sign">+</span>{line}</div>
	{/each}
</div>
