'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Nav } from '@/components/Nav';
import { authedFetch } from '@/lib/api';

type BlockingMode = 'focus-only' | 'always';

interface ApiKeyInfo {
  id: number;
  prefix: string;
  label: string;
  createdAt: string;
  lastUsedAt: string | null;
}

export default function Settings() {
  const [blocklist, setBlocklist] = useState<string[]>(['youtube.com', 'twitter.com', 'reddit.com']);
  const [newDomain, setNewDomain] = useState('');
  const [blockingMode, setBlockingMode] = useState<BlockingMode>('focus-only');

  // API keys
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [label, setLabel] = useState('');
  const [creating, setCreating] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [keyError, setKeyError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadKeys = async () => {
    try {
      const res = await authedFetch('/api/api-keys');
      if (res.ok) setKeys(await res.json());
    } catch {
      /* ignore — surfaced on create */
    }
  };

  useEffect(() => {
    loadKeys();
  }, []);

  const createKey = async () => {
    setCreating(true);
    setKeyError(null);
    setNewKey(null);
    try {
      const res = await authedFetch('/api/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.detail || `Request failed (${res.status})`);
      setNewKey(json.key);
      setLabel('');
      await loadKeys();
    } catch (err) {
      setKeyError(err instanceof Error ? err.message : 'Failed to create key');
    } finally {
      setCreating(false);
    }
  };

  const revokeKey = async (id: number) => {
    await authedFetch(`/api/api-keys/${id}`, { method: 'DELETE' });
    await loadKeys();
  };

  const copyKey = async () => {
    if (!newKey) return;
    await navigator.clipboard.writeText(newKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleAddDomain = () => {
    if (newDomain && !blocklist.includes(newDomain)) {
      setBlocklist([...blocklist, newDomain]);
      setNewDomain('');
    }
  };

  const handleRemoveDomain = (domain: string) => {
    setBlocklist(blocklist.filter((d) => d !== domain));
  };

  return (
    <div className="min-h-screen bg-background">
      <Nav />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold mb-8">Settings</h1>

        <div className="space-y-6">
          {/* API Keys */}
          <Card>
            <CardHeader>
              <CardTitle>API Keys</CardTitle>
              <CardDescription>
                Connect the browser extension. Generate a key, then paste it into the
                extension&apos;s options page so it can sync your activity to your account.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                    placeholder="Label (e.g. My laptop)"
                    className="flex-1 px-3 py-2 bg-background border border-input rounded-md
                             text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                  <button
                    onClick={createKey}
                    disabled={creating}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-md
                             text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
                  >
                    {creating ? 'Generating…' : 'Generate key'}
                  </button>
                </div>

                {keyError && <div className="text-xs text-destructive">{keyError}</div>}

                {newKey && (
                  <div className="p-3 bg-card border border-border rounded-md space-y-2">
                    <div className="text-xs text-muted-foreground">
                      Copy this key now — you won&apos;t be able to see it again.
                    </div>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 text-xs break-all text-foreground">{newKey}</code>
                      <button
                        onClick={copyKey}
                        className="text-xs px-2 py-1 rounded-md border border-border hover:bg-background transition-colors"
                      >
                        {copied ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  {keys.length === 0 ? (
                    <div className="text-sm text-muted-foreground py-2">
                      No API keys yet. Generate one to connect a device.
                    </div>
                  ) : (
                    keys.map((k) => (
                      <div
                        key={k.id}
                        className="flex items-center justify-between p-3 bg-card border border-border rounded-md"
                      >
                        <div className="min-w-0">
                          <div className="text-sm font-medium truncate">
                            {k.label || 'Untitled key'}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {k.prefix}… · {k.lastUsedAt ? 'last used recently' : 'never used'}
                          </div>
                        </div>
                        <button
                          onClick={() => revokeKey(k.id)}
                          className="text-destructive hover:text-destructive/80 text-sm font-medium transition-colors"
                        >
                          Revoke
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Blocking Mode */}
          <Card>
            <CardHeader>
              <CardTitle>Blocking Mode</CardTitle>
              <CardDescription>Choose when to block distracting websites</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <label className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="radio"
                    name="blockingMode"
                    value="focus-only"
                    checked={blockingMode === 'focus-only'}
                    onChange={(e) => setBlockingMode(e.target.value as BlockingMode)}
                    className="w-4 h-4 text-primary"
                  />
                  <div>
                    <div className="font-medium">Block only during focus sessions</div>
                    <div className="text-sm text-muted-foreground">
                      Sites are only blocked when a focus session is active
                    </div>
                  </div>
                </label>
                <label className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="radio"
                    name="blockingMode"
                    value="always"
                    checked={blockingMode === 'always'}
                    onChange={(e) => setBlockingMode(e.target.value as BlockingMode)}
                    className="w-4 h-4 text-primary"
                  />
                  <div>
                    <div className="font-medium">Block always</div>
                    <div className="text-sm text-muted-foreground">
                      Sites are blocked at all times
                    </div>
                  </div>
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Blocklist Management */}
          <Card>
            <CardHeader>
              <CardTitle>Blocklist</CardTitle>
              <CardDescription>Manage which websites to block</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddDomain()}
                    placeholder="example.com"
                    className="flex-1 px-3 py-2 bg-background border border-input rounded-md
                             text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                  <button
                    onClick={handleAddDomain}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-md
                             text-sm font-medium hover:bg-primary/90 transition-colors"
                  >
                    Add
                  </button>
                </div>

                <div className="space-y-2">
                  {blocklist.length === 0 ? (
                    <div className="text-sm text-muted-foreground py-4 text-center">
                      No blocked sites yet. Add one above.
                    </div>
                  ) : (
                    blocklist.map((domain) => (
                      <div
                        key={domain}
                        className="flex items-center justify-between p-3 bg-card border border-border rounded-md"
                      >
                        <span className="text-sm">{domain}</span>
                        <button
                          onClick={() => handleRemoveDomain(domain)}
                          className="text-destructive hover:text-destructive/80 text-sm font-medium transition-colors"
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
