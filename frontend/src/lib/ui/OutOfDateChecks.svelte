<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	interface Props {
		/** What heads the sentence, in the warning's words. */
		lead: string;
		/** The rest of it: what makes them out of date. */
		said: string;
		testId: string;
		/** What changed after they ran, under the sentence, where that is known. */
		changed?: Snippet | undefined;
		/** The checks, each a CheckRow. */
		children: Snippet;
	}

	let { lead, said, testId, changed, children }: Props = $props();
</script>

<!-- The checks that ran before the code changed, together on the warning's tint under the one sentence that says
	so, in the grid of all the checks -->
<li data-testid={testId} class="cr-ui-checks-out-of-date">
	<p class="cr-ui-checks-out-of-date-says">
		<Icon name="old" size="sm" tone="warning" />
		<span>
			<strong>{lead}</strong>
			{said}
			{#if changed}
				<span class="cr-ui-checks-changed">{@render changed()}</span>
			{/if}
		</span>
	</p>
	<ul class="cr-ui-checks-rows">
		{@render children()}
	</ul>
</li>
