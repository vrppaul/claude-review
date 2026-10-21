/**
 * Whose words a part names or is written in, said by its colour: the
 * reader's, or the agent's. A chip names a thread or a file in the colour of
 * whoever named it (Chip); a field is edged in the colour of whose thread it
 * is written in (Field, FieldButton). A turn (Turn) and a folded card's
 * summary (FoldedSummary) say who spoke by the name of their voice.
 */
export type Voice = 'reader' | 'agent';

/** What each voice is called where it is named: by its turn, or at the head of a folded card. */
export const VOICE_NAMES: Record<Voice, string> = { reader: 'You', agent: 'Agent' };
