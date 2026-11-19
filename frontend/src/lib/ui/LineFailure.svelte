<script lang="ts">
	import Icon from './Icon.svelte';

	// What a failure the code changed after says of itself at its end
	const OUT_OF_DATE = 'out of date';

	interface Props {
		/** The check that failed on the line, by its name. */
		check: string;
		/** What failed: a test, a rule. */
		what: string;
		/** Why it failed, where the check said. */
		why: string | null;
		/** Whether the line's file changed after the check ran: stepped back to ink, and said so. */
		outOfDate: boolean;
		testId: string;
	}

	let { check, what, why, outOfDate, testId }: Props = $props();
</script>

<!-- What a check found failing on a line of the code, under that line: across what draws it, on the error's tint,
	the check that found it, what failed and why. Stepped back to ink once the code changed after the check ran -->
<div data-testid={testId} class={['cr-ui-line-failure', outOfDate && 'cr-ui-line-failure-out-of-date']}>
	<span class="cr-ui-line-failure-check"><Icon name="cross" size="xs" />{check}</span>
	<span>{what}</span>
	{#if why !== null}
		<span class="cr-ui-line-failure-why">{why}</span>
	{/if}
	{#if outOfDate}
		<span class="cr-ui-line-failure-stale">{OUT_OF_DATE}</span>
	{/if}
</div>
