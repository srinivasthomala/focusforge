// Where to send someone after they sign in. Only same-site paths are allowed,
// so a crafted ?next= can't redirect users to another website.
export function safeNextPath(next: string | null | undefined, fallback = '/dashboard'): string {
  if (
    !next ||
    !next.startsWith('/') ||
    next.startsWith('//') ||
    next.includes('\\') ||
    next.includes('@')
  ) {
    return fallback;
  }
  return next;
}
