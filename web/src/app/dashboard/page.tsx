'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { WeeklyChart } from '@/components/WeeklyChart';
import Link from 'next/link';

interface DashboardData {
  todayFocusMinutes: number;
  todaySessions: number;
  distractionAttempts: number;
  topDistractions: string[];
  aiSummary: string;
  week: { date: string; minutes: number }[];
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/dashboard')
      .then((res) => res.json())
      .then((data) => {
        setData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch dashboard data:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <nav className="border-b border-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16 items-center">
              <Link href="/" className="text-xl font-bold text-primary">
                FocusForge
              </Link>
              <div className="flex space-x-4">
                <Link href="/dashboard" className="text-foreground hover:text-primary transition-colors">
                  Dashboard
                </Link>
                <Link href="/settings" className="text-muted-foreground hover:text-foreground transition-colors">
                  Settings
                </Link>
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-muted-foreground">Loading...</div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <Link href="/" className="text-xl font-bold text-primary">
              FocusForge
            </Link>
            <div className="flex space-x-4">
              <Link href="/dashboard" className="text-foreground hover:text-primary transition-colors">
                Dashboard
              </Link>
              <Link href="/settings" className="text-muted-foreground hover:text-foreground transition-colors">
                Settings
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold mb-8">Your Dashboard</h1>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Today's Focus */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Today&apos;s Focus</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="text-4xl font-bold text-primary">
                  {data?.todayFocusMinutes || 0}
                  <span className="text-lg text-muted-foreground ml-1">min</span>
                </div>
                <div className="text-sm text-muted-foreground">
                  {data?.todaySessions || 0} sessions completed
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Distractions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Distractions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="text-4xl font-bold text-destructive">
                  {data?.distractionAttempts || 0}
                </div>
                <div className="text-sm text-muted-foreground">attempts today</div>
                {data?.topDistractions && data.topDistractions.length > 0 && (
                  <div className="pt-2 space-y-1">
                    <div className="text-xs text-muted-foreground">Top sites:</div>
                    {data.topDistractions.slice(0, 2).map((site) => (
                      <div key={site} className="text-sm text-foreground">
                        {site}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* AI Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">AI Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-foreground max-h-32 overflow-y-auto">
                {data?.aiSummary || 'No summary available yet.'}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Weekly Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Weekly Focus</CardTitle>
            <CardDescription>Your focus minutes over the last 7 days</CardDescription>
          </CardHeader>
          <CardContent>
            <WeeklyChart data={data?.week || []} />
          </CardContent>
        </Card>
      </main>
    </div>
  );
}


