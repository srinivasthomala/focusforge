'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { createClient } from '@/lib/supabase/client';

export default function Login() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const sendMagicLink = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('sending');
    setError(null);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) {
      setError(error.message);
      setStatus('error');
    } else {
      setStatus('sent');
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <nav className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center">
            <Link href="/" className="text-xl font-bold text-primary">
              FocusForge
            </Link>
          </div>
        </div>
      </nav>

      <main className="flex-1 flex items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Sign in</CardTitle>
            <CardDescription>
              Enter your email and we&apos;ll send you a magic link — no password needed.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {status === 'sent' ? (
              <div className="text-sm text-foreground">
                Check <span className="font-medium">{email}</span> for a sign-in link.
                You can close this tab once you click it.
              </div>
            ) : (
              <form onSubmit={sendMagicLink} className="space-y-4">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full px-3 py-2 bg-background border border-input rounded-md
                           text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <button
                  type="submit"
                  disabled={status === 'sending'}
                  className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md
                           text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {status === 'sending' ? 'Sending…' : 'Send magic link'}
                </button>
                {error && <div className="text-xs text-destructive">{error}</div>}
              </form>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
