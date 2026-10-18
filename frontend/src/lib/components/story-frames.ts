/**
 * The frames a story's words stand in, each written once for every part of
 * the story that draws one: the agent's voice, down the edge of what it says
 * about the change; and a warning, on its wash, where to doubt a chapter,
 * that a round changed its code after it was told, and what a story costs.
 */

import type { FrameLook } from '$lib/ui/frame';

export const AGENTS_VOICE: FrameLook = { tone: 'agent', ground: 'none' };

/** The agent's voice where it did not make the change, but read it out of the code and the commits. */
export const AGENTS_READING: FrameLook = { ...AGENTS_VOICE, dashed: true };

export const A_WARNING: FrameLook = { tone: 'warning', ground: 'tint' };
