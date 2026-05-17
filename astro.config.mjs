import { defineConfig } from 'astro/config';

const isGHPages = process.env.DEPLOY_TARGET === 'gh-pages';

export default defineConfig({
  site: isGHPages ? 'https://wilsonlvin007.github.io/ailens/' : 'https://ailens.news',
  base: isGHPages ? '/ailens/' : '/',
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
