'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();

  const signOut = async () => {
    await createClient().auth.signOut();
    router.push('/login');
    router.refresh();
  };

  const linkClass = (href: string) =>
    pathname === href
      ? 'text-foreground hover:text-primary transition-colors'
      : 'text-muted-foreground hover:text-foreground transition-colors';

  return (
    <nav className="border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Link href="/" className="text-xl font-bold text-primary">
            FocusForge
          </Link>
          <div className="flex items-center space-x-4">
            <Link href="/dashboard" className={linkClass('/dashboard')}>
              Dashboard
            </Link>
            <Link href="/settings" className={linkClass('/settings')}>
              Settings
            </Link>
            <button
              onClick={signOut}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
