const pageModules = import.meta.glob('./pages/*/index.js', { eager: false });

export function resolveRoute(pathname) {
  const cleanPath = pathname.replace(/^\/+|\/+$/g, '');
  if (!cleanPath || cleanPath === '/') return null;
  const key = `./pages/${cleanPath}/index.js`;
  if (pageModules[key]) return { key, params: {} };

  // Try matching nested paths like /foo/bar
  const parts = cleanPath.split('/');
  for (let i = parts.length - 1; i > 0; i--) {
    const candidate = parts.slice(i).join('/');
    const cKey = `./pages/${candidate}/index.js`;
    if (pageModules[cKey]) return { key: cKey, params: {}, matchedPath: candidate };
  }

  return null;
}

export async function loadPage(pathname) {
  const route = resolveRoute(pathname);
  if (!route) return null;
  const module = await pageModules[route.key]();
  return module.default || module;
}
