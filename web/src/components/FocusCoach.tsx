'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { authedFetch } from '@/lib/api';

interface PendingAction {
  id: number;
  summary: string;
  status: 'pending' | 'applied' | 'cancelled' | string;
  expiresAt: string;
}

interface Turn {
  role: 'user' | 'assistant';
  text: string;
  actions?: PendingAction[];
  isError?: boolean;
}

const SUGGESTIONS = [
  'How did my focus go this week?',
  'Which sites distract me most?',
  'Block reddit.com during focus sessions',
];

async function errorDetail(res: Response, fallback: string) {
  try {
    const body = await res.json();
    if (typeof body?.detail === 'string') return body.detail;
  } catch {
    /* not JSON */
  }
  return fallback;
}

/** Chat with the FocusForge agent. Changes it proposes need a Confirm click. */
export function FocusCoach() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [limit, setLimit] = useState<number | null>(null);
  const [enabled, setEnabled] = useState(true);
  const [busyAction, setBusyAction] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    authedFetch('/api/agent/quota')
      .then((r) => (r.ok ? r.json() : null))
      .then((q) => {
        if (!q) return;
        setRemaining(q.remainingToday);
        setLimit(q.limit);
        setEnabled(q.enabled);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [turns, sending]);

  async function send(message: string) {
    const text = message.trim();
    if (!text || sending) return;

    // Prior turns as plain text, starting with a user turn (the API expects
    // user/assistant alternation). Last 10 turns at most.
    let history = turns.slice(-10).map(({ role, text }) => ({ role, text }));
    const firstUser = history.findIndex((t) => t.role === 'user');
    history = firstUser === -1 ? [] : history.slice(firstUser);

    setTurns((t) => [...t, { role: 'user', text }]);
    setInput('');
    setSending(true);
    try {
      const res = await authedFetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      });
      if (!res.ok) {
        const detail = await errorDetail(res, 'Something went wrong. Please try again.');
        if (res.status === 429) setRemaining(0);
        setTurns((t) => [...t, { role: 'assistant', text: detail, isError: true }]);
        return;
      }
      const body = await res.json();
      setRemaining(body.remainingToday);
      setTurns((t) => [
        ...t,
        { role: 'assistant', text: body.reply, actions: body.pendingActions, isError: body.status === 'error' },
      ]);
    } catch {
      setTurns((t) => [
        ...t,
        { role: 'assistant', text: 'Network error. Please try again.', isError: true },
      ]);
    } finally {
      setSending(false);
    }
  }

  async function resolveAction(id: number, verb: 'confirm' | 'cancel') {
    setBusyAction(id);
    try {
      const res = await authedFetch(`/api/agent/actions/${id}/${verb}`, { method: 'POST' });
      const updated: PendingAction | null = res.ok ? await res.json() : null;
      const failure = res.ok ? null : await errorDetail(res, 'Could not update that change.');
      setTurns((t) =>
        t.map((turn) => ({
          ...turn,
          actions: turn.actions?.map((a) =>
            a.id === id ? (updated ?? { ...a, status: failure ?? a.status }) : a
          ),
        }))
      );
    } finally {
      setBusyAction(null);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    send(input);
  }

  const outOfQuestions = remaining === 0;

  return (
    <Card className="mb-8">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>Focus Coach</CardTitle>
            <CardDescription>
              Ask about your focus data, or ask it to change what gets blocked.
            </CardDescription>
          </div>
          {enabled && remaining !== null && limit !== null && (
            <span className="shrink-0 text-xs text-muted-foreground">
              {remaining}/{limit} questions left today
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {!enabled ? (
          <p className="text-sm text-muted-foreground">
            The coach isn&apos;t enabled on this deployment.
          </p>
        ) : (
          <>
            {turns.length === 0 ? (
              <div className="flex flex-wrap gap-2 mb-4">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    disabled={sending || outOfQuestions}
                    className="text-xs px-3 py-1.5 rounded-full border border-border hover:bg-muted disabled:opacity-50 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            ) : (
              <div className="space-y-3 mb-4 max-h-80 overflow-y-auto pr-1" aria-live="polite">
                {turns.map((turn, i) => (
                  <div key={i} className={turn.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                    <div
                      className={
                        turn.role === 'user'
                          ? 'max-w-[85%] rounded-lg bg-primary text-primary-foreground px-3 py-2 text-sm'
                          : `max-w-[85%] rounded-lg bg-muted px-3 py-2 text-sm ${turn.isError ? 'text-destructive' : ''}`
                      }
                    >
                      <div className="whitespace-pre-wrap">{turn.text}</div>
                      {turn.actions?.map((a) => (
                        <div key={a.id} className="mt-2 rounded-md border border-border bg-card p-2">
                          <div className="text-xs font-medium">{a.summary}</div>
                          {a.status === 'pending' ? (
                            <div className="mt-2 flex gap-2">
                              <button
                                onClick={() => resolveAction(a.id, 'confirm')}
                                disabled={busyAction === a.id}
                                className="text-xs px-3 py-1 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                              >
                                Confirm
                              </button>
                              <button
                                onClick={() => resolveAction(a.id, 'cancel')}
                                disabled={busyAction === a.id}
                                className="text-xs px-3 py-1 rounded-md border border-border hover:bg-muted disabled:opacity-50"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <div className="mt-1 text-xs text-muted-foreground">
                              {a.status === 'applied'
                                ? 'Applied. The extension picks it up within a minute.'
                                : a.status === 'cancelled'
                                ? 'Cancelled.'
                                : a.status}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                {sending && (
                  <div className="flex justify-start">
                    <div className="rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground">
                      Looking at your data…
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            )}

            <form onSubmit={onSubmit} className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                maxLength={1000}
                disabled={sending || outOfQuestions}
                placeholder={
                  outOfQuestions ? 'No questions left today. They reset at midnight.' : 'Ask your focus coach…'
                }
                className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
              />
              <button
                type="submit"
                disabled={sending || outOfQuestions || !input.trim()}
                className="text-sm px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                Ask
              </button>
            </form>
          </>
        )}
      </CardContent>
    </Card>
  );
}
