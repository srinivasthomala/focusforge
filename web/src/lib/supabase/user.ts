import { createClient } from '@/lib/supabase/server';

/** True when the visitor has a valid session. For public pages that only
 * need to choose between "Sign in" and "Dashboard". */
export async function isSignedIn(): Promise<boolean> {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL) return false;
  try {
    const {
      data: { user },
    } = await createClient().auth.getUser();
    return Boolean(user);
  } catch {
    return false;
  }
}
