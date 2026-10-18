// Proxies the multipart upload from the browser to the n8n webhook, so the n8n URL stays server-side
// and the browser never hits CORS. Vercel caps function request bodies at ~4.5 MB; the UI shrinks
// large screenshots before sending.
const MAX_BYTES = 4.4 * 1024 * 1024;
const UPSTREAM_TIMEOUT_MS = 115_000;

const send = (res, status, body) => {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(body));
};

export default async function handler(req, res) {
  if (req.method === 'GET') {
    return send(res, 200, { ok: true, configured: Boolean(process.env.N8N_WEBHOOK_URL) });
  }
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'GET, POST');
    return send(res, 405, { ok: false, error: 'Method not allowed.' });
  }

  const target = process.env.N8N_WEBHOOK_URL;
  if (!target) {
    return send(res, 503, { ok: false, error: 'The reporter is not connected to n8n yet. Set N8N_WEBHOOK_URL in the Vercel project settings.' });
  }

  const contentType = req.headers['content-type'] || '';
  if (!contentType.startsWith('multipart/form-data')) {
    return send(res, 400, { ok: false, error: 'Expected a multipart/form-data upload.' });
  }

  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_BYTES) return send(res, 413, { ok: false, error: 'Upload is larger than 4.4 MB. Use a smaller screenshot or shorter logs.' });
    chunks.push(chunk);
  }

  const headers = { 'content-type': contentType };
  if (process.env.N8N_SHARED_SECRET) headers['x-bug-reporter-key'] = process.env.N8N_SHARED_SECRET;

  let upstream;
  try {
    upstream = await fetch(target, {
      method: 'POST',
      headers,
      body: Buffer.concat(chunks),
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
  } catch (err) {
    const timedOut = err?.name === 'TimeoutError';
    return send(res, timedOut ? 504 : 502, {
      ok: false,
      error: timedOut
        ? 'n8n took too long to answer. The bug may still be created in Jira; check the KAN board before retrying.'
        : 'Could not reach n8n. Check that the instance is running.',
    });
  }

  const text = await upstream.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    data = { ok: false, error: `n8n returned an unexpected response (HTTP ${upstream.status}).` };
  }

  if (upstream.status === 404) {
    data = { ok: false, error: 'n8n webhook not found. Make sure the workflow is active and N8N_WEBHOOK_URL is the production /webhook/ URL.' };
  }

  const ok = upstream.ok && data.ok !== false;
  return send(res, ok ? 200 : (upstream.status >= 400 ? upstream.status : 502), ok ? data : { ok: false, error: data.error || data.message || 'Bug could not be created.' });
}
