import { defineConfig } from 'vitest/config';
import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, process.cwd(), '');
	const proxyTarget = env.VITE_PROXY_TARGET || 'http://localhost:7999';
	return {
		plugins: [tailwindcss(), sveltekit()],
		ssr: {
			noExternal: ['date-picker-svelte']
		},
		server: {
			host: '0.0.0.0',
			port: 5173,
			strictPort: true,
			hmr: {
				protocol: 'ws',
				host: 'localhost',
				port: 5173,
				clientPort: 5173
			},
			proxy: {
				// Dev proxy: browser calls /presenze/* and Vite forwards to Django
				'/presenze': {
					target: proxyTarget,
					changeOrigin: true,
					secure: false
				}
			}
		},
		test: {
			expect: { requireAssertions: true },
			projects: [
				{
					extends: './vite.config.ts',
					test: {
						name: 'client',
						environment: 'browser',
						browser: {
							enabled: true,
							provider: 'playwright',
							instances: [{ browser: 'chromium' }]
						},
						include: ['src/**/*.svelte.{test,spec}.{js,ts}'],
						exclude: ['src/lib/server/**'],
						setupFiles: ['./vitest-setup-client.ts']
					}
				},
				{
					extends: './vite.config.ts',
					test: {
						name: 'server',
						environment: 'node',
						include: ['src/**/*.{test,spec}.{js,ts}'],
						exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
					},
				}
			]
		}
	};
});
