<script lang="ts">
	import type { Snippet } from 'svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { Placement, TriggerProps } from '$lib/ui/pane';
	import PaneQuestion from '$lib/ui/PaneQuestion.svelte';
	import Popover from './Popover.svelte';

	interface Props {
		/** Whether it is being asked: the control's to open, and the field's from its keys. */
		open: boolean;
		/** What is asked, as the pane says it and is named by: "Discard this comment?" */
		question: string;
		/** What the button that goes ahead says: "Discard". */
		goAhead: string;
		/** What the button that leaves things as they are says: "Keep writing". */
		keep: string;
		/** What going ahead does, once the pane is put away. */
		onGoAhead: () => void;
		/** Where it opens beside the control that asks it, where it covers nothing of what it asks about. */
		placement: Placement;
		testId: string;
		/** The control that asks it, carrying what the popover hands it. */
		trigger: Snippet<[TriggerProps]>;
	}

	let { open = $bindable(), question, goAhead, keep, onGoAhead, placement, testId, trigger }: Props = $props();

	/** Put the question away, and do what going ahead does. */
	function goAheadNow() {
		open = false;
		onGoAhead();
	}
</script>

<!-- A question before something written is lost, by the control that asked it. Its answers are its ways out:
	the safe one first, which takes the keyboard; the other loses what was written, drawn as what destroys -->
<Popover bind:open label={question} {placement} width="fitted" {testId} {trigger}>
	<div class="flex flex-col gap-3 p-3">
		<PaneQuestion {question} testId="{testId}-question" />
		<div class="flex justify-end gap-2">
			<Button tone="quiet" size="sm" testId="confirm-keep" onclick={() => (open = false)}>{keep}</Button>
			<Button tone="danger" size="sm" testId="confirm-go-ahead" onclick={goAheadNow}>{goAhead}</Button>
		</div>
	</div>
</Popover>
