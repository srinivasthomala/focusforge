// Public links used by the landing, privacy and terms pages.

// Set NEXT_PUBLIC_CHROME_STORE_URL once the Chrome Web Store listing is live.
// Until then the button points at the latest GitHub release.
export const CHROME_STORE_URL = process.env.NEXT_PUBLIC_CHROME_STORE_URL || '';
export const EXTENSION_URL =
  CHROME_STORE_URL || 'https://github.com/srinivasthomala/focusforge/releases/latest';
export const EXTENSION_CTA = CHROME_STORE_URL ? 'Add to Chrome, free' : 'Get the Chrome extension';

// Support address shown on the privacy and terms pages. Without it, those
// pages point people at GitHub issues instead.
export const CONTACT_EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL || '';

export const GITHUB_URL = 'https://github.com/srinivasthomala/focusforge';
export const ISSUES_URL = `${GITHUB_URL}/issues`;
