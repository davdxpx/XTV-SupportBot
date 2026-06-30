import { useEffect, useState } from 'react';

/**
 * Reusable in-app confirmation dialog — replaces browser `confirm()`.
 *
 * Built on the shared `.modal-backdrop` / `.modal` styling. For
 * irreversible actions pass `danger` (red confirm button) and optionally
 * `requireText` (the user must type that exact string to enable confirm,
 * e.g. the project name before a hard delete).
 */
export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = 'CONFIRM',
  cancelLabel = 'CANCEL',
  danger = false,
  requireText,
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body?: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  requireText?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [typed, setTyped] = useState('');

  // Reset the typed guard whenever the dialog (re)opens.
  useEffect(() => {
    if (open) setTyped('');
  }, [open]);

  // Esc to cancel.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) onCancel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, busy, onCancel]);

  if (!open) return null;

  const guardOk = !requireText || typed.trim() === requireText;

  return (
    <div className="modal-backdrop" onClick={() => !busy && onCancel()}>
      <div
        className="modal"
        onClick={(e) => e.stopPropagation()}
        style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 420 }}
        role="alertdialog"
        aria-modal="true"
      >
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>{title}</h2>
        {body && (
          <div style={{ fontSize: 14, color: 'var(--tg-text-dim)', lineHeight: 1.5 }}>{body}</div>
        )}

        {requireText && (
          <div className="stack" style={{ gap: 6 }}>
            <label className="label" style={{ fontSize: 11 }}>
              TYPE <code>{requireText}</code> TO CONFIRM
            </label>
            <input
              className="input"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              autoFocus
              autoComplete="off"
              placeholder={requireText}
            />
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy || !guardOk}
            className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`}
            style={{ flex: 1, padding: '12px' }}
          >
            {busy && <span className="spinner" />}
            {busy ? 'WORKING...' : confirmLabel}
          </button>
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="btn btn-ghost"
            style={{ padding: '12px 20px' }}
          >
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
