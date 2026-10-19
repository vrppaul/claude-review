import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// What the compiler's accessibility checks cannot see: a separator the
// keyboard can focus is a widget — WAI-ARIA's window splitter, which says
// how wide the column beside it is and moves with the arrow keys — and the
// checks take every separator for a plain divider. The grips that size a
// column are such splitters, and nothing else is let off.
const SPLITTER = 'src/lib/ui/EdgeGrip.svelte';
const SPLITTER_TAKEN_FOR_A_DIVIDER = new Set([
	'a11y_no_noninteractive_tabindex',
	'a11y_no_noninteractive_element_interactions'
]);

export default {
	preprocess: vitePreprocess(),
	compilerOptions: {
		runes: true,
		warningFilter: (warning) =>
			!(SPLITTER_TAKEN_FOR_A_DIVIDER.has(warning.code) && (warning.filename ?? '').endsWith(SPLITTER))
	}
};
