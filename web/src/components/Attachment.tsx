import { useEffect, useState } from 'react';
import { fetchBlobUrl } from '@/lib/api';

/**
 * Renders a ticket attachment. Images load inline (fetched as a blob so the
 * auth header/cookie rides along — a plain <img src> can't send headers);
 * other files render as a download link.
 */
export function Attachment({ path, kind }: { path: string; kind: 'photo' | 'document' }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let revoked: string | null = null;
    let cancelled = false;
    fetchBlobUrl(path)
      .then((u) => {
        if (cancelled) {
          URL.revokeObjectURL(u);
          return;
        }
        revoked = u;
        setUrl(u);
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [path]);

  if (failed) {
    return <span style={{ fontSize: 12, color: 'var(--tg-danger)' }}>📎 attachment unavailable</span>;
  }
  if (!url) {
    return <div className="skeleton skeleton-block" style={{ height: 120, maxWidth: 240 }} />;
  }
  if (kind === 'photo') {
    return (
      <a href={url} target="_blank" rel="noreferrer">
        <img
          src={url}
          alt="attachment"
          style={{ maxWidth: '100%', maxHeight: 320, border: '1px solid var(--tg-border)' }}
        />
      </a>
    );
  }
  return (
    <a href={url} download className="btn btn-ghost btn-sm" style={{ display: 'inline-flex', gap: 6 }}>
      📎 DOWNLOAD FILE
    </a>
  );
}
