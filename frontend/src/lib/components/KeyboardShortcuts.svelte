<script lang="ts">
	import { onMount } from 'svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { currentSectionPath, isTypingTarget, moveByLine } from '$lib/utils/keyboard';
	import { scrollToComment, scrollToFile } from '$lib/utils/scroll';

	let showHelp = $state(false);
	let atFile = $state(-1);

	const shortcuts: { keys: string; does: string }[] = [
		{ keys: 'j / k', does: 'Move down or up a line' },
		{ keys: 'Enter', does: 'Comment on the line you are on' },
		{ keys: '] / [', does: 'Go to the next or previous file' },
		{ keys: 'n / p', does: 'Go to the next or previous comment' },
		{ keys: 'v', does: 'Mark the file you are in as viewed' },
		{ keys: 'u', does: 'Fold or unfold the file you are in' },
		{ keys: 'Ctrl+Shift+Enter', does: 'Send the review to Claude' },
		{ keys: '?', does: 'Show this list' }
	];

	function stepFile(direction: 1 | -1) {
		const files = diffStore.files;
		if (files.length === 0) return;

		const here = currentSectionPath() ?? diffStore.selectedPath;
		const from = here ? files.findIndex((f) => f.path === here) : -1;
		atFile = from === -1 ? (direction === 1 ? 0 : files.length - 1) : from + direction;
		atFile = Math.min(files.length - 1, Math.max(0, atFile));
		scrollToFile(files[atFile].path);
	}

	function stepComment(direction: 1 | -1) {
		const comment = commentStore.step(direction);
		if (!comment) return;
		if (diffStore.isCollapsed(comment.file)) diffStore.toggleCollapsed(comment.file);
		requestAnimationFrame(() => scrollToComment(comment.id, comment.file));
	}

	function actOnCurrentFile(act: (path: string) => void) {
		const path = currentSectionPath() ?? diffStore.selectedPath;
		if (path) act(path);
	}

	function handle(event: KeyboardEvent) {
		if (event.metaKey || event.ctrlKey || event.altKey) return;
		if (isTypingTarget(event.target)) return;

		if (showHelp && event.key === 'Escape') {
			showHelp = false;
			return;
		}

		const handled: Record<string, () => void> = {
			j: () => moveByLine(1),
			k: () => moveByLine(-1),
			']': () => stepFile(1),
			'[': () => stepFile(-1),
			n: () => stepComment(1),
			p: () => stepComment(-1),
			v: () => actOnCurrentFile((path) => diffStore.toggleViewed(path)),
			u: () => actOnCurrentFile((path) => diffStore.toggleCollapsed(path)),
			'?': () => (showHelp = !showHelp)
		};

		const act = handled[event.key];
		if (!act) return;
		event.preventDefault();
		act();
	}

	onMount(() => {
		window.addEventListener('keydown', handle);
		return () => window.removeEventListener('keydown', handle);
	});
</script>

{#if showHelp}
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		role="dialog"
		aria-modal="true"
		aria-labelledby="shortcuts-title"
		tabindex="-1"
		class="fixed inset-0 z-[70] flex items-center justify-center bg-black/50"
		onclick={(e) => e.target === e.currentTarget && (showHelp = false)}
		onkeydown={(e) => e.key === 'Escape' && (showHelp = false)}
	>
		<div class="cr-dialog w-full max-w-sm rounded-lg bg-base-100 p-6">
			<h3 id="shortcuts-title" class="mb-4 text-lg font-semibold">Keyboard</h3>
			<dl data-testid="shortcuts-list" class="space-y-2">
				{#each shortcuts as shortcut (shortcut.keys)}
					<div class="flex items-baseline gap-4">
						<dt class="w-36 shrink-0 font-mono text-xs" style="color: var(--cr-mark)">
							{shortcut.keys}
						</dt>
						<dd class="text-sm">{shortcut.does}</dd>
					</div>
				{/each}
			</dl>
		</div>
	</div>
{/if}
