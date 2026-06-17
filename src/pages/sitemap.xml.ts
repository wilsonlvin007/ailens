import { getAllDates } from '../lib/data';

export async function GET() {
  const dates = getAllDates();
  const baseUrl = 'https://ailens.news';

  const lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    '  <url>',
    '    <loc>' + baseUrl + '/</loc>',
    '    <changefreq>daily</changefreq>',
    '    <priority>1.0</priority>',
    '  </url>',
    '  <url>',
    '    <loc>' + baseUrl + '/archive</loc>',
    '    <changefreq>daily</changefreq>',
    '    <priority>0.8</priority>',
    '  </url>',
    '  <url>',
    '    <loc>' + baseUrl + '/subscribe</loc>',
    '    <changefreq>monthly</changefreq>',
    '    <priority>0.4</priority>',
    '  </url>',
  ];

  for (const date of dates) {
    lines.push(
      '  <url>',
      '    <loc>' + baseUrl + '/' + date + '</loc>',
      '    <lastmod>' + date + '</lastmod>',
      '    <changefreq>weekly</changefreq>',
      '    <priority>0.6</priority>',
      '  </url>'
    );
  }

  lines.push('</urlset>');

  return new Response(lines.join('\n'), {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
}
