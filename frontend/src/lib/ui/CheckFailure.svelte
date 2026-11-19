<script lang="ts">
	interface Props {
		/** What failed there: a test, a rule. */
		what: string;
		/** Where, as `file:line`. */
		where: string;
		/** Why it failed, where the check said. */
		why: string | null;
		/** The whole of where it is, on the pointer. */
		title: string;
		testId: string;
		/** Takes the reader to where it failed; none where the review draws no such place, and it is only said. */
		onclick?: (() => void) | undefined;
	}

	let { what, where, why, title, testId, onclick }: Props = $props();
</script>

<!-- What failed, then where in the colour of a way somewhere and why, under the line of the check that failed. A kind
	of its own, not a Row: a Row says its label and words on one line, and this says what failed on a line above
	where and why, which wrap as long as the check said them -->
{#snippet said()}
	<span class="cr-ui-check-what">{what}</span>
	<span class="cr-ui-check-where">{where}</span>
	<span class="cr-ui-check-why">{why ?? ''}</span>
{/snippet}

<li data-testid={testId}>
	{#if onclick}
		<button type="button" class="cr-ui-check-failure cr-pressable" {title} {onclick}>{@render said()}</button>
	{:else}
		<div class="cr-ui-check-failure cr-ui-check-failure-unreached" {title}>{@render said()}</div>
	{/if}
</li>
