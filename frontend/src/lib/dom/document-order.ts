/** Where elements stand on the page, one against another: the order the page draws them in. */

/** Of some elements, the one that comes first in the document; null of none. */
export function firstInDocument<Found extends Element>(elements: Iterable<Found>): Found | null {
	let first: Found | null = null;
	for (const element of elements) {
		if (first === null || comesBefore(element, first)) first = element;
	}
	return first;
}

function comesBefore(element: Element, other: Element): boolean {
	return (element.compareDocumentPosition(other) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}
