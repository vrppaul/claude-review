<script lang="ts">
	interface Props {
		/** How many of the reader's threads hang on what it stands beside. */
		count: number;
		testId: string;
	}

	let { count, testId }: Props = $props();
</script>

<!-- How many of the reader's threads hang on what it stands beside — a file, a section, a part of a story — on
	their mark, in a tag's box (lib/ui/tag.ts) -->
<span data-testid={testId} class="cr-ui-count">{count}</span>
