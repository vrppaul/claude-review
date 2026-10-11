import { describe, it, expect } from 'vitest';
import { failOnUnanswered, fakeServer } from './fake-server';

describe('the server the tests stand in for the review', () => {
	it('fails the test once the page asks a route the test did not say how to answer', async () => {
		fakeServer();

		await fetch('/api/review').catch(() => undefined);

		expect(() => failOnUnanswered()).toThrow('GET /api/review');
	});

	it('answers a route by its path as the schema writes it, path parameters and all', async () => {
		const server = fakeServer();
		server.answer('DELETE /api/images/{image_id}', null);

		const answered = await fetch('/api/images/4f.png', { method: 'DELETE' });

		expect(answered.status).toBe(204);
		expect(server.requestsTo('DELETE /api/images/{image_id}')).toMatchObject([{ path: '/api/images/4f.png' }]);
	});

	it('refuses a method the route at a path does not take, as the real server does, naming those it takes', async () => {
		fakeServer();

		const refused = await fetch('/api/settings', { method: 'POST' });

		expect(refused.status).toBe(405);
		expect(refused.headers.get('Allow')).toBe('GET, PUT');
	});

	it('refuses a path it has no route at, as the real server does', async () => {
		fakeServer();

		const refused = await fetch('/api/nowhere');

		expect(refused.status).toBe(404);
		expect(await refused.json()).toEqual({ detail: 'Not Found' });
	});
});
