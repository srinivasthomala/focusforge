'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { authedFetch } from '@/lib/api';
import { createClient } from '@/lib/supabase/client';

const CONFIRM_WORD = 'DELETE';

export function DeleteAccount() {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const remove = async () => {
    setDeleting(true);
    setError(null);
    try {
      const res = await authedFetch('/api/account', { method: 'DELETE' });
      if (res.status !== 204) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || "Couldn't delete your account. Please try again.");
      }
      // The sign-in no longer exists; clear the local session too.
      await createClient().auth.signOut().catch(() => {});
      window.location.assign('/?deleted=1');
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't delete your account. Please try again.");
      setDeleting(false);
    }
  };

  return (
    <Card className="border-destructive/40">
      <CardHeader>
        <CardTitle className="text-destructive">Delete account</CardTitle>
        <CardDescription>
          Permanently delete your account and everything stored with it: focus sessions, blocked attempts,
          blocked sites, AI summaries, Focus Coach history and extension keys. This can&apos;t be undone.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!open ? (
          <button
            onClick={() => setOpen(true)}
            className="text-sm px-4 py-2 rounded-md border border-destructive/60 text-destructive hover:bg-destructive/10 transition-colors"
          >
            Delete my account
          </button>
        ) : (
          <div className="space-y-3">
            <label htmlFor="confirm-delete" className="block text-sm">
              Type <strong>{CONFIRM_WORD}</strong> to confirm.
            </label>
            <input
              id="confirm-delete"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              autoComplete="off"
              disabled={deleting}
              className="w-full max-w-xs rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-destructive/40"
            />
            {error && <div className="text-sm text-destructive">{error}</div>}
            <div className="flex gap-2">
              <button
                onClick={remove}
                disabled={typed !== CONFIRM_WORD || deleting}
                className="text-sm px-4 py-2 rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50 transition-colors"
              >
                {deleting ? 'Deleting…' : 'Permanently delete'}
              </button>
              <button
                onClick={() => {
                  setOpen(false);
                  setTyped('');
                  setError(null);
                }}
                disabled={deleting}
                className="text-sm px-4 py-2 rounded-md border border-border hover:bg-muted transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
