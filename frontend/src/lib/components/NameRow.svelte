<script lang="ts" module>
	import type { DefinitionKind } from '$lib/types';

	// What of the names outlining a file is called, and so written with the brackets a call takes after its name
	const CALLED: ReadonlySet<DefinitionKind> = new Set(['function']);
	// What a name that is called is written with after it
	const CALL_BRACKETS = '()';
</script>

<script lang="ts">
	import type { TouchedName } from '$lib/types';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import RowWithAct from '$lib/ui/RowWithAct.svelte';
	import Sought from '$lib/ui/Sought.svelte';
	import StatusLetter from '$lib/ui/StatusLetter.svelte';
	import { NAME_LETTERS } from './status-letters';

	/** The way to where a name is defined and used from its row: whether its pane is open, and how to ask. */
	interface LookingUp {
		open: boolean;
		/** Ask about the name from the icon pressed, or close its pane where it is open. */
		toggle: (icon: HTMLButtonElement) => void;
	}

	interface Props {
		name: TouchedName;
		/** What the tree's filter was typed, lit where it stands in the name. */
		sought: string;
		/** How many folders deep it stands in the tree of files: a step past its file. */
		depth: number;
		/** Whether it is the first name under its file, whose branch starts under the file's letter. */
		first: boolean;
		/** Whether the reader is in it now: the line they read from is one of its lines. */
		current: boolean;
		/** Whether the reader has finished with its file: it steps back with the file. */
		viewed: boolean;
		onclick: () => void;
		/** The way to where it is defined and used, at the row's end; none where the review cannot look it up. */
		lookingUp: LookingUp | undefined;
	}

	let { name, sought, depth, first, current, viewed, onclick, lookingUp }: Props = $props();

	const letter = $derived({ ...NAME_LETTERS[name.change], said: name.change });
</script>

{#snippet leading()}
	<StatusLetter {...letter} />
{/snippet}

{#snippet label()}
	<Sought words={name.name} {sought} testId="name-sought" />{#if CALLED.has(name.defined_as)}<span class="cr-faint"
			>{CALL_BRACKETS}</span
		>{/if}
{/snippet}

<!-- The way to where it is defined and used, where the review can look it up -->
{#snippet lookUp()}
	{#if lookingUp !== undefined}
		{@const way = lookingUp}
		<IconButton
			tone="quiet"
			size="xs"
			shape="square"
			label="Where {name.name} is defined and used"
			testId="name-look-up"
			aria-haspopup="dialog"
			aria-expanded={way.open}
			onclick={(event: MouseEvent & { currentTarget: HTMLButtonElement }) => way.toggle(event.currentTarget)}
		>
			<Icon name="lookup" size="sm" />
		</IconButton>
	{/if}
{/snippet}

<!-- A name of the code the change touched, on a branch off its file in the tree: what became of it, the name as the
	code writes it, and one press to where it is defined; at its end, in sight while the row is reached, the way to
	where it is defined and used, pressed while its pane is open -->
<li>
	<RowWithAct
		names="code-name"
		testId="name-item"
		{depth}
		branch={first ? 'first' : 'next'}
		{current}
		{viewed}
		aria-current={current ? 'true' : undefined}
		{onclick}
		{leading}
		{label}
		act={lookUp}
		actShown="while-reached"
	/>
</li>
