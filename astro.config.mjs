import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://ailens.news',
  output: 'static',
  build: {
    assets: 'assets',
  },
  vite: {
    build: {
      cssMinify: true,
    },
  },
});
