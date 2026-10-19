<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	interface Props {
		/** Whether what it marks is done: a file read through. */
		checked: boolean;
		/** The test id of its box, which is what is pressed. */
		testId: string;
		/** Called as the reader ticks or unticks it, with whether it is ticked now. */
		onToggle: (checked: boolean) => void;
		/** What it says, after the box it draws. */
		children: Snippet;
	}

	let { checked, testId, onToggle, children }: Props = $props();
</script>

<!-- A choice that is on or off drawn as a chip among a header's controls, the whole of it the box to press: its
	checkbox laid over all of it unseen, its own box drawn as an icon, ticked once what it marks is done -->
<label class="cr-ui-check-chip cr-pressable">
	<input type="checkbox" data-testid={testId} {checked} onchange={(event) => onToggle(event.currentTarget.checked)} />
	<Icon name={checked ? 'ticked' : 'box'} size="xs" />
	{@render children()}
</label>
