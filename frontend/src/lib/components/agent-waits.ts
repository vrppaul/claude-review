/**
 * What is said of something waiting on the agent — a message in the panel,
 * a question in a thread — once the agent has stopped listening, what
 * taking back the unanswered is called, and what asking it now is called:
 * one set of words wherever it waits. And what is said of words the agent
 * was handed while the reader rewrote them.
 */

/** Said in place of how long it has been worked on, or waited for, once the agent has stopped listening. */
export const AGENT_STOPPED_LISTENING = 'The agent stopped listening before it answered';

/** What taking back a message or a question still unanswered is called. */
export const TAKE_BACK = 'Take back';

/** What is asked before it is taken back, and what leaves it with the agent. */
export const TAKE_IT_BACK = 'Take it back?';
export const KEEP_WAITING = 'Keep waiting';

/** What is said under a message or a question taken back, after the words that say it was. */
export const ASKED_TO_DROP_IT = 'The agent was asked to drop it.';

/** What handing what the reader wrote to the agent at once is called, on every button that does it. */
export const ASK_AGENT_NOW = 'Ask agent now';

/** Said where Ask agent now would stand, while no agent is there to hear it. */
export const NOBODY_LISTENING = 'No agent listening: this goes with the next round';

/**
 * Said where the keys of words being rewritten stand, once the agent was handed them as they were: it reads them
 * once, so they cannot be saved over, and what the reader means now goes in a reply.
 */
export const HANDED_WHILE_REWRITTEN = 'The agent has read these words now: say it in a reply';
