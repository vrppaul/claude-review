import './styles/main.css';
import { mount } from 'svelte';

import App from './App.svelte';
import { PageConnection, sessionUrl } from '$lib/connection/page-connection';
import { ReviewPage } from '$lib/page/review-page.svelte';

const page = new ReviewPage(new PageConnection(sessionUrl(window.location)));

const target = document.getElementById('app');
if (target === null) throw new Error('index.html has no #app to draw in');

mount(App, { target, props: { page } });

void page.open();
