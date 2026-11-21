<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { filesOutsideTheChange } from '$lib/review/files-way';
	import type { FoundOutside } from '$lib/review/names-outside.svelte';
	import type { NameDefined } from '$lib/types';
	import Heading from '$lib/ui/Heading.svelte';
	import Row from '$lib/ui/Row.svelte';
	import Standing from '$lib/ui/Standing.svelte';
	import { fileName, folderOf } from '$lib/utils/paths';
	import { counted, type CountedWords } from '$lib/utils/words';
	import CodeNameWords from './CodeNameWords.svelte';
	import FileRow from './FileRow.svelte';

	interface Props {
		/** The names outside the change the tree's filter finds: none while nothing is typed, or names are not listed. */
		found: FoundOutside;
		/** What the filter was typed, lit where it stands in a name. */
		sought: string;
		/** What each name's row announces itself by to the filter, which hands the keyboard to the first it finds. */
		foundRole: string;
	}

	let { found, sought, foundRole }: Props = $props();

	// What the line under the names found says, counting those not listed
	const MORE_NAMES: CountedWords = { one: 'more name', many: 'more names' };

	const review = useReview();

	// The files the change did not touch, under its own, and the one of them read alone now
	const readAlone = $derived(review.views.fileReadAlone);
	const outside = $derived(filesOutsideTheChange(review.threads, review.diff, readAlone));

	/** Go to where a name is defined: a file the change did not touch is read alone. */
	function goTo(name: NameDefined) {
		void review.navigator.goToLine(
			name.path,
			{ side: 'new', number: name.line },
			{ column: name.column, name: name.name }
		);
	}
</script>

{#if outside.length > 0 || found.names.length > 0}
	<!-- Under the change's own files, what it did not touch: the files the reader reads or left something in, one
		press to read each alone; and the names the filter finds, one press to where each is defined -->
	<div data-testid="not-in-this-change" class="mt-3 flex flex-col gap-1">
		<Heading tag="h3" heads="list" testId="not-in-this-change-heading">Not in this change</Heading>
		{#if outside.length > 0}
			<ul>
				{#each outside as path (path)}
					<FileRow
						testId="outside-file"
						status={null}
						current={path === readAlone}
						threads={review.threads.onLinesOf(path).length}
						title={path}
						onclick={() => void review.navigator.readAlone(path)}
					>
						{#snippet name()}
							{fileName(path)}
						{/snippet}
						{#snippet end()}
							<span class="cr-faint text-xs">{folderOf(path)}</span>
						{/snippet}
					</FileRow>
				{/each}
			</ul>
		{/if}
		{#if found.names.length > 0}
			<ul data-testid="outside-names">
				{#each found.names as name (`${name.path}:${name.name}`)}
					<li>
						<!-- Drawn as the file rows above it are, a path; the file it is in at the row's end, cut before the
							name is, as the name is what the reader typed -->
						<Row
							names="path"
							testId="outside-name"
							title={name.path}
							saidAt="end"
							data-role={foundRole}
							onclick={() => goTo(name)}
						>
							{#snippet label()}
								<CodeNameWords
									name={name.name}
									definedAs={name.defined_as}
									{sought}
									soughtTestId="outside-name-sought"
								/>
							{/snippet}
							{#snippet said()}
								{fileName(name.path)}
							{/snippet}
						</Row>
					</li>
				{/each}
			</ul>
			{#if found.more > 0}
				<Standing tone="faint" stands="under-a-list" testId="outside-names-more"
					>{counted(found.more, MORE_NAMES)}</Standing
				>
			{/if}
		{/if}
	</div>
{/if}
