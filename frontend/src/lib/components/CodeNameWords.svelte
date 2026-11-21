<script lang="ts" module>
	import type { DefinitionKind } from '$lib/types';

	// What of the names outlining a file is called, and so written with the brackets a call takes after its name
	const CALLED: ReadonlySet<DefinitionKind> = new Set(['function']);
	// What a name that is called is written with after it
	const CALL_BRACKETS = '()';
</script>

<script lang="ts">
	import Sought from '$lib/ui/Sought.svelte';

	interface Props {
		name: string;
		definedAs: DefinitionKind;
		/** What the tree's filter was typed, lit where it stands in the name. */
		sought: string;
		/** What the stretch lit is known by. */
		soughtTestId: string;
	}

	let { name, definedAs, sought, soughtTestId }: Props = $props();
</script>

<!-- A name of the code as a row of the tree writes it: what the filter found lit, and a callable's brackets, quieter -->
<Sought words={name} {sought} testId={soughtTestId} />{#if CALLED.has(definedAs)}<span class="cr-faint"
		>{CALL_BRACKETS}</span
	>{/if}
