<script lang="ts">
	import { ICONS, type IconName, type IconShape } from './icons';

	/**
	 * How large an icon is drawn: as tall as words of that size, so one beside words stands as tall as they do.
	 * - xs: beside small words, and in a small button
	 * - sm: beside words of the body's size
	 * - base: in a button that ends a pane or a bar, and beside a heading
	 * - xl: a mark that stands for what it is beside, or for nothing yet
	 */
	type IconSize = 'xs' | 'sm' | 'base' | 'xl';
	/** Which way an icon that points is turned: each is drawn pointing down. */
	type Pointing = 'down' | 'up' | 'left' | 'right';

	// The class of each size and each turn in the library's stylesheet; pointing down, as drawn, it is not turned
	const SIZES: Record<IconSize, string> = {
		xs: 'cr-ui-icon-xs',
		sm: 'cr-ui-icon-sm',
		base: 'cr-ui-icon-base',
		xl: 'cr-ui-icon-xl'
	};
	const TURNS: Record<Pointing, string | null> = {
		down: null,
		up: 'cr-ui-icon-up',
		left: 'cr-ui-icon-left',
		right: 'cr-ui-icon-right'
	};

	interface Props {
		name: IconName;
		size: IconSize;
		pointing?: Pointing;
		/** What the icon says on its own, for whoever cannot see it; without one it is left unsaid, as words beside it say it. */
		label?: string;
		/** For an icon that is a mark the tests look for: a file viewed, a part read. */
		testId?: string;
	}

	let { name, size, pointing = 'down', label, testId }: Props = $props();

	const shape: IconShape = $derived(ICONS[name]);
	const traced = $derived(shape.drawn.kind === 'traced' ? shape.drawn : null);
</script>

<!-- An icon, drawn once in ICONS: in the colour of the words it stands in, at the size its caller names -->
<svg
	viewBox={shape.viewBox}
	fill={traced ? 'none' : 'currentColor'}
	stroke={traced ? 'currentColor' : undefined}
	stroke-width={traced?.width}
	stroke-linecap={traced ? 'round' : undefined}
	stroke-linejoin={traced ? 'round' : undefined}
	role={label ? 'img' : undefined}
	aria-label={label}
	aria-hidden={label ? undefined : 'true'}
	data-testid={testId}
	class={['cr-ui-icon', SIZES[size], TURNS[pointing]]}
>
	{#each shape.paths as path (path)}
		<path d={path} />
	{/each}
</svg>
