<script lang="ts">
	import { FIELD_VOICES } from './field';
	import type { Voice } from './voice';

	interface Props {
		/** What the field it opens says before anything is written in it: "Reply…". */
		placeholder: string;
		/** Whose thread the field it opens is written in. */
		voice: Voice;
		testId: string;
		/** Open the field to write in, in its place. */
		onclick: () => void;
	}

	let { placeholder, voice, testId, onclick }: Props = $props();
</script>

<!-- A field not begun: a press, drawn as the empty field it opens, at its corner and edge and saying what that
	field says before anything is written in it (lib/ui/field.ts) -->
<button
	type="button"
	data-testid={testId}
	class={['cr-ui-field cr-ui-field-button cr-pressable', FIELD_VOICES[voice]]}
	{onclick}
>
	{placeholder}
</button>
