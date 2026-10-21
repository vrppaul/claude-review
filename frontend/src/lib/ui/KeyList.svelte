<script lang="ts">
	import Key from './Key.svelte';

	// What stands between two keys that do opposite things: a slash, as what they do is written
	const OPPOSITES_APART = ' / ';

	/** A row of the list: one key, or two that do opposite things in the order `does` names them; and what they do. */
	interface ListedKeys {
		keys: readonly string[];
		does: string;
	}

	interface Props {
		/** The keys and what each does, a row to each thing done. */
		rows: readonly ListedKeys[];
		testId: string;
		/** The test id of every key it draws. */
		keyTestId: string;
	}

	let { rows, testId, keyTestId }: Props = $props();
</script>

<!-- Keys listed against what they do, as a list of terms: two columns, the keys right-aligned against their words -->
<dl data-testid={testId} class="cr-ui-key-list">
	{#each rows as row (row.does)}
		<div class="cr-ui-key-list-row">
			<dt class="cr-ui-key-list-keys">
				{#each row.keys as key, position (key)}
					{#if position > 0}{OPPOSITES_APART}{/if}<Key keys={key} stands="listed" testId={keyTestId} />
				{/each}
			</dt>
			<dd class="cr-ui-key-list-does">{row.does}</dd>
		</div>
	{/each}
</dl>
