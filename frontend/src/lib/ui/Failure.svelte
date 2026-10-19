<script lang="ts">
	/**
	 * Where it stands: in a line of its own, under what could not be done; or among the words and controls of a
	 * line, beside what could not be done.
	 */
	type Stands = 'apart' | 'inline';

	interface Props {
		stands: Stands;
		testId: string;
		/** Why it could not be done, as the review or the browser said it. */
		said: string;
	}

	let { stands, testId, said }: Props = $props();
</script>

<!-- Why something the reader did could not be done, in the colour of what fails and at the size of small words,
	the same wherever it is said -->
{#if stands === 'apart'}
	<p data-testid={testId} class="cr-ui-failure">{said}</p>
{:else}
	<span data-testid={testId} class="cr-ui-failure">{said}</span>
{/if}
