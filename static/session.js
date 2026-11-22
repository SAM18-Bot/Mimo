// All authenticated requests from student pages are relative to this Mimo server.
async function mimoFetch(resource, options = {}) {
  const url = new URL(resource, location.href);
  if (url.origin !== location.origin) throw new Error('Invalid API origin');
  const headers = new Headers(options.headers);
  const token = localStorage.getItem('mimo_token');
  if (token && !headers.has('Authorization')) headers.set('Authorization', 'Bearer ' + token);
  const response = await fetch(url, { ...options, headers });
  if (response.status === 401 && !url.pathname.startsWith('/auth/') &&
      token && token === localStorage.getItem('mimo_token')) {
    localStorage.removeItem('mimo_token');
    await window.pywebview?.api?.report_token?.('');
    location.replace('/');
  }
  return response;
}
