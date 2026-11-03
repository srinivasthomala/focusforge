import { createClient } from '@/lib/supabase/client';

/**
 * fetch() wrapper that attaches the current Supabase access token as a
 * Bearer header. The Next.js rewrite forwards it to the FastAPI backend,
 * which resolves it to the authenticated user.
 */
export async function authedFetch(path: string, init: RequestInit = {}) {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = new Headers(init.headers);
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`);
  }
  // The API buckets activity into the user's local days ("today", the weekly
  // chart), so tell it which zone the browser is in, e.g. "Asia/Kolkata".
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz) headers.set('X-Timezone', tz);
  } catch {
    /* very old browser: the API falls back to the saved zone, then UTC */
  }
  return fetch(path, { ...init, headers });
}
