import { promises as dns } from 'dns';
import { URL } from 'url';

const BLOCKED_HOSTS = new Set(['metadata.google.internal', 'metadata.goog']);

function isBlockedIp(ip: string): boolean {
  // IPv4 private/loopback/link-local/multicast/broadcast
  if (ip.includes('.')) {
    const parts = ip.split('.').map(Number);
    if (parts.length !== 4 || parts.some((p) => Number.isNaN(p))) return true;
    const [a, b] = parts;
    return (
      a === 10 ||
      a === 127 ||
      a === 0 ||
      (a === 169 && b === 254) ||
      (a === 172 && b >= 16 && b <= 31) ||
      (a === 192 && b === 168) ||
      a >= 224
    );
  }
  // IPv6 — block loopback, link-local, unique-local, multicast, unspecified
  const lower = ip.toLowerCase();
  return (
    lower === '::1' ||
    lower === '::' ||
    lower.startsWith('fe80:') ||
    lower.startsWith('fc') ||
    lower.startsWith('fd') ||
    lower.startsWith('ff')
  );
}

/**
 * Throws if the URL targets a private/loopback/link-local address or a known
 * cloud-metadata host. Used to block SSRF in webhook dispatch.
 */
export async function assertSafeUrl(rawUrl: string): Promise<void> {
  let parsed: URL;
  try {
    parsed = new URL(rawUrl);
  } catch {
    throw new Error(`Invalid URL: ${rawUrl}`);
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new Error(`URL scheme not allowed: ${parsed.protocol}`);
  }

  const host = parsed.hostname;
  if (!host) throw new Error('URL has no hostname');
  if (BLOCKED_HOSTS.has(host.toLowerCase())) {
    throw new Error(`Hostname not allowed: ${host}`);
  }

  const records = await dns.lookup(host, { all: true });
  for (const rec of records) {
    if (isBlockedIp(rec.address)) {
      throw new Error(`Host resolves to blocked address: ${host} → ${rec.address}`);
    }
  }
}
