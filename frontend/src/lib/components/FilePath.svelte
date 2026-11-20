<script lang="ts">
	interface Props {
		/** Where the file a heading names is. */
		path: string;
		/** Where it was, for a file the change moved; none for any other. */
		formerPath: string | null;
	}

	let { path, formerPath }: Props = $props();
</script>

<!-- A file's path as a heading says it, wherever its lines are drawn: whole among the files, a piece of it in a story,
	or a file read alone. Moved, where it was stands quieter before it, the space after the arrow inside its words, so
	nothing stands before the path of a file not moved -->
{#if formerPath}<span class="cr-muted font-normal">{`${formerPath} → `}</span>{/if}{path}
