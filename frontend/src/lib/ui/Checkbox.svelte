<script lang="ts">
	interface Props {
		/** Whether the choice it stands for is on. */
		checked: boolean;
		testId: string;
		/** Called as the reader ticks or unticks it, with whether it is ticked now. */
		onToggle: (checked: boolean) => void;
	}

	let { checked, testId, onToggle }: Props = $props();
</script>

<!-- A box ticked or not, for a choice that is on or off, in the colour of the reader's controls: the words that say
	the choice stand beside it, in the label that holds both, so a press on them ticks it too -->
<input
	type="checkbox"
	data-testid={testId}
	class="cr-ui-checkbox"
	{checked}
	onchange={(event) => onToggle(event.currentTarget.checked)}
/>
