<script lang="ts">
	import type { HTMLTextareaAttributes } from 'svelte/elements';
	import { FIELD_HOLDS, FIELD_VOICES, type FieldHolds } from './field';
	import type { Voice } from './voice';

	// What sets how tall it stands is what it holds: no caller sizes it by rows or columns of its own
	interface Props extends Omit<HTMLTextareaAttributes, 'class' | 'style' | 'value' | 'children' | 'rows' | 'cols'> {
		/** What it holds, which sets how tall it stands and whether it grows with what is written. */
		holds: FieldHolds;
		/** Whose thread it is written in. */
		voice: Voice;
		testId: string;
		/** What is written in it. */
		value: string;
		/** The field itself, for whoever hands the keyboard to it or reads where its caret stands. */
		element?: HTMLTextAreaElement | undefined;
	}

	let { holds, voice, testId, value = $bindable(), element = $bindable(), ...attributes }: Props = $props();

	const drawn = $derived(FIELD_HOLDS[holds]);

	// Grown with what is written, where it grows: a suggestion inserts several lines at once, and a fixed box
	// would scroll them out of sight with nothing to say so. How tall it may grow is the stylesheet's
	$effect(() => {
		void value;
		if (element && drawn.grows) fitToText(element);
	});

	/** As tall as the words in it: measured from nothing, as only the field itself can say. */
	function fitToText(field: HTMLTextAreaElement) {
		field.style.height = 'auto';
		field.style.height = `${field.scrollHeight}px`;
	}
</script>

<!-- A field the reader writes in, in the reading face of a comment, edged in the colour of whose thread it is
	written in (lib/ui/field.ts): what it is handed besides lands on the element, and its test id and look are
	the library's alone, written after it -->
<textarea
	bind:this={element}
	bind:value
	{...attributes}
	data-testid={testId}
	class={['cr-ui-field cr-comment-body cr-ui-field-written', drawn.drawnAs, FIELD_VOICES[voice]]}
></textarea>
