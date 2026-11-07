import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { safeNextPath } from '@/lib/next-path';

/** Exchanges the magic-link code for a session, then redirects to the dashboard. */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');
  const cookieNext = cookies().get('ff_next')?.value;
  const next = safeNextPath(searchParams.get('next') ?? (cookieNext ? decodeURIComponent(cookieNext) : null));

  if (code) {
    const supabase = createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      const response = NextResponse.redirect(`${origin}${next}`);
      response.cookies.delete('ff_next');
      return response;
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth`);
}
