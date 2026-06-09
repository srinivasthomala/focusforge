'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';

type BlockingMode = 'focus-only' | 'always';

export default function Settings() {
  const [blocklist, setBlocklist] = useState<string[]>([
    'youtube.com',
    'twitter.com',
    'reddit.com',
  ]);
  const [newDomain, setNewDomain] = useState('');
  const [blockingMode, setBlockingMode] = useState<BlockingMode>('focus-only');

  const handleAddDomain = () => {
    if (newDomain && !blocklist.includes(newDomain)) {
      setBlocklist([...blocklist, newDomain]);
      setNewDomain('');
    }
  };

  const handleRemoveDomain = (domain: string) => {
    setBlocklist(blocklist.filter((d) => d !== domain));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleAddDomain();
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <Link href="/" className="text-xl font-bold text-primary">
              FocusForge
            </Link>
            <div className="flex space-x-4">
              <Link href="/dashboard" className="text-muted-foreground hover:text-foreground transition-colors">
                Dashboard
              </Link>
              <Link href="/settings" className="text-foreground hover:text-primary transition-colors">
                Settings
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold mb-8">Settings</h1>

        <div className="space-y-6">
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
                {/* Add domain input */}
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    onKeyPress={handleKeyPress}
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

                {/* Blocklist */}
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


