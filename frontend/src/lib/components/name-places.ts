/**
 * What the pane of a name looked up says and lists, from what the review
 * answered: its places in three groups — where it is defined, where it is
 * used and the change did not touch the line, where the change used it —
 * each group's places under the file they are in. The review says which
 * place is which; the page lays them out in the order it gave them.
 */

import type { NamePlace, NameResponse } from '$lib/types';
import { counted, type CountedWords } from '$lib/utils/words';

/** A place as the pane lists it, with where its way stands among the ways the pane lists: the keyboard's order. */
export interface ListedPlace {
	place: NamePlace;
	position: number;
}

/** The places of one file listed in a group, under its path. */
interface PlacesInFile {
	path: string;
	places: ListedPlace[];
}

/** A group of places as the pane lists it: its heading, how many it holds, what it shows of them and what waits. */
export interface ListedGroup {
	heading: string;
	testId: string;
	count: number;
	files: PlacesInFile[];
	/** How many of its places wait behind the way to show them. */
	waiting: number;
	/** Where the way to the first place waiting stands among the pane's ways, once the group is shown whole. */
	firstWaiting: number;
}

/** A group the pane lists places in: what heads it, what it is known by, and which places are its. */
interface Group {
	heading: string;
	testId: string;
	holds: (place: NamePlace) => boolean;
}

// The groups, in the order they stand: the uses the change did not touch before its own, as what the agent may
// have forgotten
const GROUPS: readonly Group[] = [
	{ heading: 'Defined', testId: 'name-defined', holds: (place) => place.defined_as !== null },
	{
		heading: 'Used where the change did not touch',
		testId: 'name-used-untouched',
		holds: (place) => place.defined_as === null && !place.added
	},
	{
		heading: 'Used in this change',
		testId: 'name-used-in-the-change',
		holds: (place) => place.defined_as === null && place.added
	}
];
// How many places of a group show before the rest wait behind a way to show them
const SHOWN_AT_FIRST = 6;

const DEFINITIONS: CountedWords = { one: 'definition', many: 'definitions' };
const USES: CountedWords = { one: 'use', many: 'uses' };
// What the count says in place of the definitions where there are none
const NOT_DEFINED_HERE = 'not defined here';

/** What the review found of a name, as the pane's notes read it: its places, and how many of them define it. */
interface Found {
	name: NameResponse;
	definitions: number;
}

/** A note the pane says before the places, where a reader could take the list wrongly: when, and its words. */
interface Note {
	stands: (found: Found) => boolean;
	says: (found: Found) => string;
}

const NOTES: readonly Note[] = [
	// No definition found: the name may come with the language or a library, or be defined where the review reads
	// none, as a loop's target or an import
	{
		stands: ({ definitions }) => definitions === 0,
		says: () => 'No definition of this name was found in the repository.'
	},
	// Several definitions: the uses are found by spelling, not by which of them each means
	{
		stands: ({ definitions }) => definitions > 1,
		says: ({ name, definitions }) =>
			`${definitions} things are called ${name.name}. The review finds a name by how it is spelled, so the uses are of all of them.`
	},
	// Places found as words in text no grammar reads: a file of no grammar the review has, a Svelte component's markup
	{
		stands: ({ name }) => name.places.some((place) => place.found_as === 'text'),
		says: () => 'Some places are this word found in text the review has no grammar for, so they may not be this name.'
	}
];

/** The groups that hold a place, their places listed under their files: a group's first few, or all of it once shown. */
export function listedGroups(found: NameResponse, shownWhole: ReadonlySet<string>): ListedGroup[] {
	const listed: ListedGroup[] = [];
	let position = 0;
	for (const group of GROUPS) {
		const places = found.places.filter(group.holds);
		if (places.length === 0) continue;
		const shown = shownWhole.has(group.testId) ? places : places.slice(0, SHOWN_AT_FIRST);
		const files = byFile(shown.map((place, index) => ({ place, position: position + index })));
		position += shown.length;
		listed.push({
			heading: group.heading,
			testId: group.testId,
			count: places.length,
			files,
			waiting: places.length - shown.length,
			firstWaiting: position
		});
	}
	return listed;
}

/** Where the way to a place stands among the ways the groups list; none where it is not listed. */
export function positionOf(groups: ListedGroup[], place: NamePlace): number | null {
	const listed = groups.flatMap((group) => group.files.flatMap((file) => file.places));
	return listed.find((shown) => shown.place === place)?.position ?? null;
}

/** The place the pane lists first: none where the review found none. */
export function firstListed(found: NameResponse): NamePlace | null {
	return listedGroups(found, new Set())[0]?.files[0]?.places[0]?.place ?? null;
}

/** How many definitions and uses: "2 definitions, 12 uses", "not defined here, 24 uses". */
export function countSaid(found: NameResponse): string {
	const definitions = definitionsOf(found);
	const uses = found.places.length - definitions;
	const defined = definitions === 0 ? NOT_DEFINED_HERE : counted(definitions, DEFINITIONS);
	return `${defined}, ${counted(uses, USES)}`;
}

/** What the pane says of the places before it lists them: what a reader could take wrongly from the list. */
export function notesOn(name: NameResponse): string[] {
	const found = { name, definitions: definitionsOf(name) };
	return NOTES.filter((note) => note.stands(found)).map((note) => note.says(found));
}

/** How many of a name's places define it. */
function definitionsOf(found: NameResponse): number {
	return found.places.filter((place) => place.defined_as !== null).length;
}

/** Places under the file each is in, the files in the order their first place comes. */
function byFile(places: ListedPlace[]): PlacesInFile[] {
	const grouped = Map.groupBy(places, ({ place }) => place.path);
	return [...grouped].map(([path, inFile]) => ({ path, places: inFile }));
}
