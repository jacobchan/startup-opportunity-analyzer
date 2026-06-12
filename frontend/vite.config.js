/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            '/runs': 'http://localhost:8000',
            '/evidence': 'http://localhost:8000',
        },
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: [],
        passWithNoTests: true,
    },
});
