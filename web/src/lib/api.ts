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
  return fetch(path, { ...init, headers });
}
