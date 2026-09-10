<script lang="ts">
	import { diffStore } from '$lib/stores/diff.svelte';
	import type { ReviewVersion, VersionKind } from '$lib/types';

	let open = $state(false);
	let filter = $state('');
	let failed = $state<string | null>(null);
	let asking = $state(false);
	let container = $state<HTMLElement>();
	let trigger = $state<HTMLButtonElement>();

	const sections: { kind: VersionKind; title: string }[] = [
		{ kind: 'review', title: 'This review' },
		{ kind: 'round', title: 'Rounds' },
		{ kind: 'ref', title: 'Branches and tags' }
	];

	const matching = $derived(
		diffStore.versions.filter((v) => v.label.toLowerCase().includes(filter.trim().toLowerCase()))
	);
	const hasRounds = $derived(diffStore.versions.some((v) => v.kind === 'round'));

	async function show() {
		open = !open;
		if (!open) return;
		filter = '';
		failed = null;
		asking = true;
		try {
			await diffStore.fetchVersions();
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not list what this can be compared against';
		} finally {
			asking = false;
		}
	}

	/** Close, and give the keyboard back where it came from. */
	function shut() {
		open = false;
		trigger?.focus();
	}

	async function pick(version: ReviewVersion) {
		failed = null;
		try {
			await diffStore.setBase(version.key);
			shut();
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not take the diff against that';
		}
	}

	/** What a row says about a base on its right: its size, or its age. */
	function meta(version: ReviewVersion): string {
		if (version.changed !== null) {
			return `${version.changed} ${version.changed === 1 ? 'file' : 'files'}`;
		}
		if (version.at === null) return '';
		const seconds = Math.max(0, Math.round((Date.now() - version.at) / 1000));
		if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
		if (seconds < 86_400) return `${Math.round(seconds / 3600)}h ago`;
		return `${Math.round(seconds / 86_400)}d ago`;
	}
</script>

<svelte:window
	onclick={(e) => {
		if (open && container && !container.contains(e.target as Node)) open = false;
	}}
	onkeydown={(e) => {
		if (e.key === 'Escape' && open) shut();
	}}
/>

<div class="relative" bind:this={container}>
	<!-- The second half of the title, made a control: the header still reads
		as one sentence, and takes the mark tint while a narrower base is on. -->
	<button
		data-testid="base-picker"
		class="cr-chip font-mono"
		style={diffStore.narrowed
			? 'background: var(--cr-mark-tint); color: var(--color-base-content)'
			: ''}
		aria-expanded={open}
		title="What the working tree is compared against"
		bind:this={trigger}
		onclick={show}
	>
		<svg
			class="h-3 w-3 shrink-0"
			style={diffStore.narrowed ? 'color: var(--cr-mark)' : ''}
			viewBox="0 0 16 16"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<path d="M2.5 5h9" />
			<path d="M9 2.5L11.5 5 9 7.5" />
			<path d="M13.5 11h-9" />
			<path d="M7 8.5L4.5 11 7 13.5" />
		</svg>
		{diffStore.phrase}
		<svg class="h-3 w-3 shrink-0" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
			<path d="M2 4l4 4 4-4z" />
		</svg>
	</button>

	{#if open}
		<div
			data-testid="base-list"
			class="cr-dialog absolute left-0 z-30 mt-2 w-80 overflow-hidden rounded-box bg-base-200"
		>
			<div class="px-3 pt-2 pb-1">
				<p class="cr-muted text-xs">Compare the working tree against</p>
				<!-- svelte-ignore a11y_autofocus -->
				<input
					data-testid="base-filter"
					class="mt-2 w-full rounded border border-base-300 bg-base-100 px-2 py-1 font-mono text-xs"
					placeholder="filter"
					autofocus
					bind:value={filter}
				/>
			</div>

			{#each sections as section (section.kind)}
				{@const listed = matching.filter((v) => v.kind === section.kind)}
				{#if listed.length > 0}
					<p class="cr-faint px-3 pt-2 pb-1 text-xs">{section.title}</p>
					{#each listed as version (version.key)}
						<button
							data-testid="base-option"
							class="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-base-300"
							style={version.key === diffStore.base ? 'background: var(--cr-mark-tint)' : ''}
							onclick={() => pick(version)}
						>
							<span class="w-3 shrink-0">
								{#if version.key === diffStore.base}
									<svg
										class="h-3 w-3"
										style="color: var(--cr-mark)"
										viewBox="0 0 12 12"
										fill="currentColor"
										aria-label="In force"
									>
										<path d="M4.6 8.8L2 6.2l.9-.9 1.7 1.7L9.1 2.4l.9.9z" />
									</svg>
								{/if}
							</span>
							<span class="flex-1 truncate font-mono text-xs">{version.label}</span>
							<span class="cr-faint shrink-0 text-xs">{meta(version)}</span>
						</button>
					{/each}
				{/if}
			{/each}

			{#if asking && matching.length === 0}
				<p data-testid="bases-asking" class="cr-muted px-3 py-6 text-center text-xs">
					Asking git what this can be read against…
				</p>
			{:else if matching.length === 0 && !failed}
				<p data-testid="no-bases" class="cr-muted px-3 py-6 text-center text-xs">
					{filter.trim() ? 'Nothing here answers to that.' : 'Nothing to compare against.'}
				</p>
			{/if}

			{#if failed}
				<p data-testid="base-error" class="border-t border-base-300 px-3 py-2 text-xs text-error">
					{failed}
				</p>
			{/if}

			{#if hasRounds}
				<p class="cr-faint border-t border-base-300 px-3 py-2 text-xs">
					Rounds are kept for as long as this review is open.
				</p>
			{/if}
		</div>
	{/if}
</div>
