/**
 * Who says a turn (Avatar), drawn round by their glyph on a ground of their
 * colour: the reader or the agent (Voice); or the reader's turn not said
 * yet, beside the field to reply in, in grey. Its look is written in
 * styles/ui.css.
 */

import type { Voice } from './voice';

export type AvatarTone = Voice | 'unsaid';
