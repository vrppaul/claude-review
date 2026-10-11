<script lang="ts">
	import type { SVGAttributes } from 'svelte/elements';
	import { ICONS, type IconName, type IconShape } from './icons';

	interface Props extends SVGAttributes<SVGSVGElement> {
		name: IconName;
		/** What the icon says on its own, for whoever cannot see it; without one it is left unsaid, as words beside it say it. */
		label?: string;
	}

	let { name, label, ...drawnWith }: Props = $props();

	const shape: IconShape = $derived(ICONS[name]);
	const traced = $derived(shape.drawn.kind === 'traced' ? shape.drawn : null);
</script>

<svg
	{...drawnWith}
	viewBox={shape.viewBox}
	fill={traced ? 'none' : 'currentColor'}
	stroke={traced ? 'currentColor' : undefined}
	stroke-width={traced?.width}
	stroke-linecap={traced ? 'round' : undefined}
	stroke-linejoin={traced ? 'round' : undefined}
	role={label ? 'img' : undefined}
	aria-label={label}
	aria-hidden={label ? undefined : 'true'}
>
	{#each shape.paths as path (path)}
		<path d={path} />
	{/each}
</svg>
