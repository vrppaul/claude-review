import { describe, it, expect } from 'vitest';

describe("the tests' stand-in for a modal dialog", () => {
	it('says a dialog closed once, however often it is closed', () => {
		const dialog = document.createElement('dialog');
		document.body.append(dialog);
		let closings = 0;
		dialog.addEventListener('close', () => (closings += 1));

		dialog.showModal();
		dialog.close();
		dialog.close();

		expect(closings).toBe(1);
		dialog.remove();
	});
});
