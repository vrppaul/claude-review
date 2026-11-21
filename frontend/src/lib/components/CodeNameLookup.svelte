<script lang="ts">
	import type { NamesInTheCode } from '$lib/review/names-in-the-code.svelte';
	import CodeMark from '$lib/ui/CodeMark.svelte';
	import { holdsModifiersOf, LOOKUP_CHORD } from './keymap';
	import NameLookupPane from './NameLookupPane.svelte';

	interface Props {
		/** The names of the code of the reading area the marks and the pane stand in. */
		names: NamesInTheCode;
	}

	let { names }: Props = $props();

	const asked = $derived(names.lookup.asked);

	/** The key the gesture is held with went down or up: the word under the pointer is marked while it is held. */
	function noteKey(event: KeyboardEvent) {
		names.hold(holdsModifiersOf(LOOKUP_CHORD, event));
	}
</script>

<!-- On the window: the key goes down or up wherever the keyboard is, and a window left lets it go unseen -->
<svelte:window onkeydown={noteKey} onkeyup={noteKey} onblur={() => names.hold(false)} />

<!-- The lookup of names in a reading area's code: the word under the pointer marked while the key is held, the name
	pressed marked while its pane or its window is open, and the pane by it, scrolling with the code -->
{#if names.held}
	<CodeMark stretch={() => names.held} mark="held" marks={names.marks} testId="name-held" />
{/if}
{#if asked}
	<CodeMark stretch={asked.from.name.stretch} mark="pressed" marks={names.marks} testId="name-pressed" />
{/if}
<NameLookupPane lookup={names.lookup} />
