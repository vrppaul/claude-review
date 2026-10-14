/**
 * What the page says of a diagram it could not draw.
 *
 * Mermaid says why in words of its own. Where one of its parsers stopped,
 * the error it throws also says on which line, and at what text: the page
 * says that instead, since mermaid's words point at the place with a caret
 * under a copy of the line, which reads only in a monospaced font.
 */

import { messageOf } from '$lib/utils/errors';

// What is said before why
const NOT_DRAWN = 'This diagram could not be drawn:';

/** Where a parser of mermaid's stopped on a source, as it hangs it on the error it throws. */
interface ParserStop {
	/** The text it did not expect there. */
	text: string;
	/** Where that text begins: its line, counted from one. */
	loc: { first_line: number };
}

/** Whether a value is an object, whose fields can be asked after. */
function isObject(value: unknown): value is object {
	return typeof value === 'object' && value !== null;
}

/** Whether what an error carries says where a parser stopped. */
function isParserStop(carried: unknown): carried is ParserStop {
	return (
		isObject(carried) &&
		'text' in carried &&
		typeof carried.text === 'string' &&
		'loc' in carried &&
		isObject(carried.loc) &&
		'first_line' in carried.loc &&
		typeof carried.loc.first_line === 'number'
	);
}

/** Where a parser stopped, as a fault says it: on what mermaid's parsers call its `hash`. */
function parserStop(fault: unknown): ParserStop | null {
	return isObject(fault) && 'hash' in fault && isParserStop(fault.hash) ? fault.hash : null;
}

/** What stopped mermaid, said: where a parser stopped, or else mermaid's own words. */
function faultWords(fault: unknown): string {
	const stop = parserStop(fault);
	return stop === null ? messageOf(fault) : `line ${stop.loc.first_line}, unexpected "${stop.text.trim()}"`;
}

/** That a diagram could not be drawn, and why, as mermaid threw it. */
export function diagramNotDrawn(fault: unknown): string {
	return `${NOT_DRAWN} ${faultWords(fault)}.`;
}
