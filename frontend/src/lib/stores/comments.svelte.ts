import type { Comment, SubmitResponse } from '$lib/types';

let comments = $state<Comment[]>([]);
let reviewBody = $state('');
let submitted = $state(false);

let nextId = 0;

function generateId(): string {
	return `comment-${++nextId}`;
}

export const commentStore = {
	get comments() {
		return comments;
	},
	get count() {
		return comments.length;
	},
	get reviewBody() {
		return reviewBody;
	},
	get hasContent() {
		return comments.length > 0 || reviewBody.trim().length > 0;
	},
	get submitted() {
		return submitted;
	},

	setReviewBody(text: string) {
		reviewBody = text;
	},

	add(file: string, startLine: number, endLine: number, body: string) {
		const comment: Comment = {
			id: generateId(),
			file,
			start_line: startLine,
			end_line: endLine,
			body
		};
		comments = [...comments, comment];
		return comment.id;
	},

	update(id: string, body: string) {
		comments = comments.map((c) => (c.id === id ? { ...c, body } : c));
	},

	remove(id: string) {
		comments = comments.filter((c) => c.id !== id);
	},

	getForFile(file: string): Comment[] {
		return comments.filter((c) => c.file === file);
	},

	getForLine(file: string, line: number): Comment[] {
		return comments.filter((c) => c.file === file && c.end_line === line);
	},

	clear() {
		comments = [];
		reviewBody = '';
		submitted = false;
		nextId = 0;
	},

	async submit(): Promise<SubmitResponse> {
		const trimmedBody = reviewBody.trim();
		const payload = {
			comments: comments.map(({ file, start_line, end_line, body }) => ({
				file,
				start_line,
				end_line,
				body
			})),
			...(trimmedBody ? { body: trimmedBody } : {})
		};

		const response = await fetch('/api/submit', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});

		if (!response.ok) {
			throw new Error(`Submit failed: ${response.status}`);
		}

		const result: SubmitResponse = await response.json();
		submitted = true;
		return result;
	}
};
