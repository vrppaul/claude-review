<script lang="ts">
	import type { Snippet } from 'svelte';

	/** What it does, by the colour it is said in: an act like any other, or one that destroys. */
	type MenuItemTone = 'plain' | 'danger';

	// The class of each in the library's stylesheet
	const MENU_ITEM_TONES: Record<MenuItemTone, string | null> = { plain: null, danger: 'cr-ui-menu-item-danger' };

	interface Props {
		tone: MenuItemTone;
		testId: string;
		/** Its icon, drawing the act, and its name. */
		children: Snippet;
		onclick: () => void;
	}

	let { tone, testId, children, onclick }: Props = $props();
</script>

<!-- An act a menu offers, a row of its own as tall as a list's: its icon, then its name, lit under the pointer -->
<button type="button" data-testid={testId} class={['cr-ui-menu-item cr-pressable', MENU_ITEM_TONES[tone]]} {onclick}>
	{@render children()}
</button>
