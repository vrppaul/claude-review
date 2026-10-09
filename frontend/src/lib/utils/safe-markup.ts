/**
 * Writing text that came from somebody else into HTML without letting it run.
 *
 * The text is a file out of the repository under review, an agent's answer or
 * a transcript: none of it is ours. Script running in the review's origin can
 * read the diff and the repository and send comments of its own for an agent
 * to act on, so every value that reaches the markup goes through here.
 */

// What would close a text node or a quoted attribute early, as entities
const MARKUP_ENTITIES: Readonly<Record<string, string>> = {
	'&': '&amp;',
	'<': '&lt;',
	'>': '&gt;',
	'"': '&quot;',
	"'": '&#39;'
};
const MARKUP_SPECIAL = /[&<>"']/g;

// Schemes a link or an image may lead to. Anything else — javascript:, data:,
// vbscript: — is not a destination, it is code or content carried inline.
const SAFE_PROTOCOLS = new Set(['http:', 'https:', 'mailto:']);

// What a relative destination is read against. Never fetched: it only lets the
// parser tell a path from a scheme. A relative path resolves onto it and takes
// its protocol, which is a safe one.
const RELATIVE_BASE = 'https://relative.invalid/';

/** Text made safe for a text node and for a quoted attribute value alike. */
export function escapeMarkup(text: string): string {
	return text.replace(MARKUP_SPECIAL, (special) => MARKUP_ENTITIES[special]);
}

/**
 * Whether a link or an image may point where it says.
 *
 * Read with the browser's own URL rules rather than by pattern: the browser
 * drops tabs and newlines inside a URL and control characters around it, so
 * "java\tscript:" is javascript: to it, and a pattern that does not do the
 * same lets it through.
 */
export function isSafeDestination(destination: string): boolean {
	try {
		return SAFE_PROTOCOLS.has(new URL(destination, RELATIVE_BASE).protocol);
	} catch {
		return false;
	}
}
