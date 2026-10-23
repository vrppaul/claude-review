/**
 * The frames a story's words stand in, each written once for every part of
 * the story that draws one: the agent's voice, down the edge of a step's
 * reason; and a warning, on its tint, of what a story costs.
 */

import type { EdgeLook } from '$lib/ui/frame';

export const AGENTS_VOICE: EdgeLook = { shape: 'edge', tone: 'agent', ground: 'none' };

export const A_WARNING: EdgeLook = { shape: 'edge', tone: 'warning', ground: 'tint' };
