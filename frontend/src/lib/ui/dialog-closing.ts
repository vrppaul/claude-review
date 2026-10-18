/**
 * The ways a dialog is closed from what it holds, handed to that by name:
 * a button's handler takes the one it means, and none is told from the
 * other by where it stands in a list.
 */
export interface Closing {
	/** Close it as Escape does, so the browser gives the keyboard back. */
	close: () => void;
	/** Close it, and then do something: for what must find the keyboard back where it was. */
	closeThen: (then: () => void) => void;
}
