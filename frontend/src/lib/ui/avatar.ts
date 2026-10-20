/**
 * Who says a turn of a conversation (Turn), drawn by their avatar (Avatar),
 * round, by their glyph on a ground of their colour: the reader or the agent
 * (Voice); or the reader whose turn is not said yet, beside the field to
 * reply in, in grey. Its look is written in styles/ui.css.
 */

import type { Voice } from './voice';

export type Speaker = Voice | 'unsaid';
