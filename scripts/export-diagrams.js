#!/usr/bin/env node
/**
 * Export all .excalidraw files in diagrams/ to SVG using a headless browser.
 * Usage: npm run export-diagrams
 */

const { chromium } = require('playwright');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const DIAGRAMS_DIR = path.join(ROOT, 'diagrams');
const BUNDLE = path.join(__dirname, 'excalidraw-render.bundle.js');

function buildBundle() {
  process.stdout.write('Building Excalidraw render bundle... ');
  execSync(
    `npx esbuild ${path.join(__dirname, 'excalidraw-render.mjs')}` +
    ` --bundle --outfile=${BUNDLE}` +
    ` --platform=browser` +
    ` --define:process.env.NODE_ENV='"production"'`,
    { cwd: ROOT }
  );
  console.log('done');
}

async function main() {
  const files = fs.readdirSync(DIAGRAMS_DIR)
    .filter(f => f.endsWith('.excalidraw'))
    .map(f => path.join(DIAGRAMS_DIR, f));

  if (files.length === 0) {
    console.log('No .excalidraw files found in diagrams/');
    return;
  }

  buildBundle();

  console.log(`Exporting ${files.length} diagram(s)...`);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('console', () => {});
  page.on('pageerror', () => {});

  await page.setContent('<!DOCTYPE html><html><head><meta charset="utf-8"></head><body></body></html>');
  await page.addScriptTag({ path: BUNDLE });

  const ready = await page.evaluate(() => typeof window.__exportDiagram === 'function');
  if (!ready) {
    console.error('Error: render bundle did not load correctly.');
    await browser.close();
    process.exit(1);
  }

  for (const file of files) {
    const name = path.basename(file, '.excalidraw');
    const data = JSON.parse(fs.readFileSync(file, 'utf8'));
    process.stdout.write(`  ${name}.excalidraw → ${name}.svg ... `);

    const svg = await page.evaluate(async (diagram) => {
      return await window.__exportDiagram(diagram);
    }, data);

    const outPath = path.join(DIAGRAMS_DIR, `${name}.svg`);
    fs.writeFileSync(outPath, svg);
    console.log('done');
  }

  await browser.close();

  // Clean up bundle artifact
  fs.unlinkSync(BUNDLE);

  console.log(`\nSVGs written to diagrams/`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
