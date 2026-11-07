import type { Metadata } from 'next';
import { Contact, LegalPage } from '@/components/LegalPage';

export const metadata: Metadata = {
  title: 'Privacy Policy | FocusForge',
  description: 'What FocusForge collects, why, and how to delete it.',
};

export default function Privacy() {
  return (
    <LegalPage title="Privacy Policy" updated="November 7, 2026">
      <p>
        FocusForge is a focus timer and site blocker made of a Chrome extension, a web dashboard and an API. This
        policy explains what data it collects, why, and the choices you have. The short version: we collect only
        what is needed to show you your own focus stats, we never sell it, and we never use it for ads.
      </p>

      <h2>What the extension does on your computer</h2>
      <p>
        To block sites, the extension checks the address of each page you open against your list of blocked sites.
        This check happens in your browser. The extension does <strong>not</strong> send or store your browsing
        history. Pages that are not on your blocked list are never recorded.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li>
          <strong>Account details:</strong> your email address, and your name and profile picture if you sign in
          with Google. Sign-in is handled by Supabase.
        </li>
        <li>
          <strong>Focus sessions:</strong> when each session started and ended, and how many minutes you focused.
        </li>
        <li>
          <strong>Blocked attempts:</strong> when you try to open a blocked site during a session (or at any time
          if you choose to block always), the extension records that page address, its domain and the time.
        </li>
        <li>
          <strong>Settings:</strong> your blocked sites, blocking mode and time zone.
        </li>
        <li>
          <strong>AI features:</strong> your daily summaries, and the questions you ask the Focus Coach with its
          answers.
        </li>
        <li>
          <strong>Extension keys:</strong> the key that connects the extension to your account. We store only a
          one-way hash of it.
        </li>
      </ul>
      <p>
        The extension also keeps your settings, timer state and any unsent session records in Chrome&apos;s local
        storage on your computer.
      </p>

      <h2>How we use it</h2>
      <ul>
        <li>To show your focus time, sessions and blocked attempts on your dashboard.</li>
        <li>To sync your blocked sites between the dashboard and the extension.</li>
        <li>To write your daily summary and answer your Focus Coach questions.</li>
        <li>To keep the service safe, for example with usage limits.</li>
      </ul>

      <h2>AI processing</h2>
      <p>
        Daily summaries and the Focus Coach use Claude, an AI model from Anthropic. When you use them, the
        relevant focus statistics (such as minutes focused and the domains of blocked sites) and your question are
        sent to Anthropic&apos;s API to produce the answer. Anthropic does not use data sent through its API to
        train its models by default.
      </p>

      <h2>Who processes your data</h2>
      <p>We use these service providers to run FocusForge:</p>
      <ul>
        <li>Supabase, for sign-in.</li>
        <li>Neon, for the database.</li>
        <li>Fly.io, for the API servers.</li>
        <li>Vercel, for the website.</li>
        <li>Anthropic, for the AI features.</li>
      </ul>
      <p>We do not sell your data, share it with advertisers, or use it to build profiles for ads.</p>

      <h2>Chrome Web Store Limited Use</h2>
      <p>
        FocusForge&apos;s use of information received from the Chrome extension follows the Chrome Web Store User
        Data Policy, including the Limited Use requirements. Data is used only to provide the features described
        above, is not transferred except as needed to provide them, and is never used for advertising or credit
        decisions.
      </p>

      <h2>How long we keep it</h2>
      <p>
        We keep your data while your account exists. When you ask us to delete your account, we delete your
        sessions, blocked attempts, settings, summaries, Focus Coach history and keys.
      </p>

      <h2>Your choices</h2>
      <ul>
        <li>You can use the timer and blocking without an account. Nothing is sent until you connect one.</li>
        <li>You can disconnect the extension at any time by clearing its key in the extension settings.</li>
        <li>
          You can ask for a copy of your data, or for your account and data to be deleted, by contacting us at{' '}
          <Contact />.
        </li>
      </ul>

      <h2>Security</h2>
      <p>
        All traffic is encrypted with HTTPS. Each account can only read its own data, and extension keys are stored
        as hashes.
      </p>

      <h2>Children</h2>
      <p>FocusForge is not meant for children under 13, and we do not knowingly collect their data.</p>

      <h2>Changes</h2>
      <p>
        If we change this policy, we will update the date at the top of this page. For important changes we will
        also let you know on the dashboard.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about privacy? Reach us at <Contact />.
      </p>
    </LegalPage>
  );
}
