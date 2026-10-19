<script lang="ts">
	interface Props {
		/** How many of the reader's threads hang on what it stands beside. */
		count: number;
		/** Kept from a screen reader, where the name of what it stands in says how many in words. */
		'aria-hidden'?: boolean | undefined;
		testId: string;
	}

	let { count, 'aria-hidden': unsaid, testId }: Props = $props();
</script>

<!-- How many of the reader's threads hang on what it stands beside — a file, a section, a part of a story — on
	their mark, in a tag's box (lib/ui/tag.ts) -->
<span aria-hidden={unsaid} data-testid={testId} class="cr-ui-count">{count}</span>
