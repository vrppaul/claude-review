<script lang="ts">
	import type { Snippet } from 'svelte';
	import Confirmation from './Confirmation.svelte';
	import type { Placement, TriggerProps } from './pane';
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

<!-- A question before something is lost, in a pane by the control that asked it (Confirmation) -->
<Popover bind:open label={question} {placement} width="fitted" {testId} {trigger}>
	<Confirmation {question} {goAhead} {keep} onKeep={() => (open = false)} onGoAhead={goAheadNow} {testId} />
</Popover>
