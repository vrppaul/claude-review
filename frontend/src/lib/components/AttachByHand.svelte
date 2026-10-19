<script lang="ts">
	import CodeBox from '$lib/ui/CodeBox.svelte';
	import Row from '$lib/ui/Row.svelte';

	// What attaches an agent by hand to a review started in the foreground: the review again in the background,
	// and its listening half in a loop
	const ATTACH_BY_HAND = 'claude-review diff --no-open &\nclaude-review wait --port <port> --until-event';

	// Whether the commands are open: folded away each time they are drawn, until asked for
	let open = $state(false);
</script>

<!-- How to attach an agent by hand, for whoever started the review themselves: folded away under its question -->
<div data-testid="attach-by-hand" class="w-full text-left">
	<Row names="title" folded={!open} testId="panel-attach-by-hand" onclick={() => (open = !open)}>
		{#snippet label()}
			Started the review yourself?
		{/snippet}
	</Row>
	{#if open}
		<div class="mt-2 flex flex-col gap-2">
			<p class="cr-faint text-xs">
				Nothing answers a review run in the foreground. Start it in the background and keep the listening half in a
				loop:
			</p>
			<CodeBox code={ATTACH_BY_HAND} testId="attach-commands" />
		</div>
	{/if}
</div>
