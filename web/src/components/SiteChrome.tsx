import Link from 'next/link';
import { EXTENSION_CTA, EXTENSION_URL, GITHUB_URL } from '@/lib/site';

// Header and footer for the public pages (landing, privacy, terms).

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="text-xl font-bold text-primary">
          FocusForge
        </Link>
        <nav className="flex items-center gap-5 text-sm">
          <Link href="/#features" className="hidden text-muted-foreground hover:text-foreground sm:inline">
            Features
          </Link>
          <Link href="/#how" className="hidden text-muted-foreground hover:text-foreground sm:inline">
            How it works
          </Link>
          <Link href="/#faq" className="hidden text-muted-foreground hover:text-foreground md:inline">
            FAQ
          </Link>
          <Link href="/login" className="text-muted-foreground hover:text-foreground">
            Sign in
          </Link>
          <a
            href={EXTENSION_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden rounded-md bg-primary px-4 py-2 font-semibold text-primary-foreground hover:bg-primary/90 sm:inline-block"
          >
            {EXTENSION_CTA}
          </a>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-10 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <span className="font-semibold text-foreground">FocusForge</span> · Built by Srinivas Thomala
        </div>
        <div className="flex flex-wrap gap-5">
          <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
          <Link href="/terms" className="hover:text-foreground">Terms</Link>
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="hover:text-foreground">
            GitHub
          </a>
          <Link href="/login" className="hover:text-foreground">Sign in</Link>
        </div>
      </div>
    </footer>
  );
}
