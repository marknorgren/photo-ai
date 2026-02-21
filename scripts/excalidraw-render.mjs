// Browser-side entry point bundled by esbuild.
// Exposes window.__exportDiagram for use by the Playwright script.
import { exportToSvg } from '@excalidraw/excalidraw';

window.__exportDiagram = async (data) => {
  const el = await exportToSvg({
    elements: data.elements,
    appState: {
      exportWithDarkMode: false,
      exportBackground: true,
      theme: 'light',
    },
    files: data.files ?? null,
  });
  return el.outerHTML;
};
