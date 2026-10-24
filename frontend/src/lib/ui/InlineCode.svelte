<script lang="ts">
	/**
	 * What the code is, which sets how it is drawn:
	 * - command: a command the reader types in the agent's session, at the words' size
	 * - path: a file's path, a step smaller, broken anywhere so a long one wraps in its line
	 */
	type Kind = 'command' | 'path';

	// The class of each in the library's stylesheet
	const KINDS: Record<Kind, string | null> = { command: null, path: 'cr-ui-inline-code-path' };

	interface Props {
		/** The code as it is written: `/review-ui`, `src/app.py`. */
		code: string;
		kind: Kind;
	}

	let { code, kind }: Props = $props();
</script>

<!-- Code said among words, as the browser marks it up: in the code's face and in ink, plainer than the words round
	it -->
<code class={['cr-ui-inline-code', KINDS[kind]]}>{code}</code>
