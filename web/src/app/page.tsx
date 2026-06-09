import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8">
      <div className="max-w-4xl w-full text-center space-y-8">
        <div className="space-y-4">
          <h1 className="text-6xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            FocusForge
          </h1>
          <p className="text-2xl text-muted-foreground">
            Forge your focus. Shape your day.
          </p>
        </div>

        <p className="text-lg text-foreground/80 max-w-2xl mx-auto">
          A lightweight focus and productivity tool designed for developers and creators. 
          Block distractions, track your focus sessions, and gain insights into your productivity.
        </p>

        <div className="pt-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center rounded-md text-sm font-medium 
                     bg-primary text-primary-foreground hover:bg-primary/90 
                     h-11 px-8 py-2 transition-colors"
          >
            Go to Dashboard
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-12 text-left">
          <div className="p-6 rounded-lg bg-card border border-border">
            <h3 className="text-lg font-semibold mb-2">Block Distractions</h3>
            <p className="text-sm text-muted-foreground">
              Keep distracting websites at bay during your focus sessions
            </p>
          </div>
          <div className="p-6 rounded-lg bg-card border border-border">
            <h3 className="text-lg font-semibold mb-2">Track Progress</h3>
            <p className="text-sm text-muted-foreground">
              See how much time you spend focused vs distracted
            </p>
          </div>
          <div className="p-6 rounded-lg bg-card border border-border">
            <h3 className="text-lg font-semibold mb-2">AI Insights</h3>
            <p className="text-sm text-muted-foreground">
              Get personalized summaries of your productivity patterns
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}


