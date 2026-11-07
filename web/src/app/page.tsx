import Image from 'next/image';
import Link from 'next/link';
import { SiteFooter, SiteHeader } from '@/components/SiteChrome';
import { EXTENSION_CTA, EXTENSION_URL, GITHUB_URL } from '@/lib/site';

const features = [
  {
    title: 'A timer that fits your work',
    body: 'Pick 15, 25, 45, 60 or 90 minutes, or type any length up to 4 hours. Add 5 minutes when you are on a roll. Time left shows on the toolbar icon.',
  },
  {
    title: 'Distractions blocked',
    body: 'Add the sites that pull you away. They are blocked during focus sessions, or all the time if you prefer.',
  },
  {
    title: 'Your week at a glance',
    body: 'See focus time per day, sessions completed and which sites you tried to open, all on one dashboard.',
  },
  {
    title: 'Focus Coach',
    body: 'Ask questions like "How did my focus go this week?" and get answers from your own data. It can suggest blocking a site, and nothing changes until you confirm.',
  },
  {
    title: 'AI daily summary',
    body: 'One click turns your day into a short summary with one practical tip for tomorrow.',
  },
  {
    title: 'Private by design',
    body: 'FocusForge does not record your browsing history. It only saves your session times and the blocked sites you tried to open.',
  },
];

const steps = [
  { n: '1', title: 'Add the extension', body: 'Install FocusForge in Chrome. It opens a short setup page.' },
  { n: '2', title: 'Create a free account', body: 'Sign up with email or Google, then connect the extension with one key.' },
  { n: '3', title: 'Start a session', body: 'Pick a length and work. Blocked sites stay closed until the timer ends.' },
];

const faqs = [
  {
    q: 'Is FocusForge free?',
    a: 'Yes. The timer, blocking, dashboard and daily summary are free. The Focus Coach is free for 5 questions a day.',
  },
  {
    q: 'Does it track the websites I visit?',
    a: 'No. The extension checks each page against your blocked list on your own computer. It only sends your session start and end times, and the blocked sites you tried to open, so your dashboard can show them.',
  },
  {
    q: 'Which browsers does it work in?',
    a: 'Chrome, and other Chromium browsers that support Chrome extensions, such as Edge and Brave.',
  },
  {
    q: 'Can I use the timer without an account?',
    a: 'Yes. The timer and blocking work on their own. You need a free account to sync your blocked sites, see your stats and use the Focus Coach.',
  },
  {
    q: 'Can I delete my data?',
    a: 'Yes. Ask us and we will delete your account and all its data. See the privacy policy for details.',
  },
  {
    q: 'Is it open source?',
    a: 'Yes, under the MIT license. The full code for the web app, API and extension is on GitHub.',
  },
];

function PopupMockup() {
  return (
    <div className="w-[300px] rounded-xl border border-border bg-[#0f172a] p-5 shadow-2xl shadow-black/50">
      <div className="mb-4 flex items-baseline justify-between">
        <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-lg font-bold text-transparent">
          FocusForge
        </span>
        <span className="text-[11px] text-slate-400">Forge your focus</span>
      </div>
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <div className="text-center text-4xl font-bold tabular-nums text-teal-500">38:12</div>
        <div className="mt-1 text-center text-xs text-slate-400">of 45 min</div>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-900">
          <div className="h-full w-[15%] rounded-full bg-gradient-to-r from-teal-500 to-cyan-500" />
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm font-semibold">
        <div className="rounded-md border border-slate-700 bg-slate-800 py-2.5 text-center text-slate-200">+5 min</div>
        <div className="rounded-md bg-red-500 py-2.5 text-center text-white">End session</div>
      </div>
      <div className="mt-3 flex justify-between text-xs text-slate-400">
        <span>
          Status: <b className="text-slate-200">Focusing</b>
        </span>
        <span>
          Distractions blocked: <b className="text-slate-200">3</b>
        </span>
      </div>
      <div className="mt-3 border-t border-slate-700 pt-3">
        <div className="mb-2 text-xs font-semibold text-slate-400">Blocked sites</div>
        {['youtube.com', 'reddit.com', 'instagram.com'].map((d) => (
          <div key={d} className="mb-1 rounded bg-slate-800 px-2 py-1.5 text-xs text-slate-300">
            {d}
          </div>
        ))}
      </div>
    </div>
  );
}

function CoachMockup() {
  return (
    <div className="w-full max-w-md rounded-xl border border-border bg-card p-5 shadow-2xl shadow-black/50">
      <div className="text-lg font-bold">Focus Coach</div>
      <div className="mb-4 text-xs text-muted-foreground">Ask about your focus data, or ask it to change what gets blocked.</div>
      <div className="space-y-3 text-sm">
        <div className="ml-auto w-fit max-w-[85%] rounded-lg bg-primary px-3 py-2 text-primary-foreground">
          How did my focus go this week?
        </div>
        <div className="w-fit max-w-[90%] rounded-lg bg-muted px-3 py-2">
          6 h 40 m across 14 sessions. Tuesday was your best day at 2 h 10 m. You tried to open youtube.com 9
          times during sessions.
        </div>
        <div className="ml-auto w-fit max-w-[85%] rounded-lg bg-primary px-3 py-2 text-primary-foreground">
          Block x.com too
        </div>
        <div className="w-fit max-w-[90%] rounded-lg bg-muted px-3 py-2">
          <div className="mb-2">Here is the change. It applies only when you confirm.</div>
          <div className="rounded-md border border-border bg-background p-3">
            <div className="mb-2 font-semibold">Block x.com</div>
            <div className="flex gap-2">
              <span className="rounded-md bg-primary px-3 py-1 text-primary-foreground">Confirm</span>
              <span className="rounded-md border border-border px-3 py-1">Cancel</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="min-h-screen">
      <SiteHeader />

      <main>
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute left-1/2 top-[-200px] h-[500px] w-[900px] -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
          <div className="relative mx-auto max-w-6xl px-4 pb-16 pt-16 text-center sm:px-6 sm:pt-24">
            <div className="mx-auto mb-6 w-fit rounded-full border border-primary/30 bg-primary/10 px-4 py-1 text-sm text-primary">
              Free Chrome extension with an AI focus coach
            </div>
            <h1 className="mx-auto max-w-4xl text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
              Block distractions. <span className="text-primary">Focus longer.</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
              FocusForge blocks the sites that pull you away while you work, tracks your focus time, and gives
              you a coach that answers questions about your own habits.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <a
                href={EXTENSION_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-12 items-center rounded-md bg-primary px-8 font-semibold text-primary-foreground hover:bg-primary/90"
              >
                {EXTENSION_CTA}
              </a>
              <Link
                href="/login?mode=signup"
                className="inline-flex h-12 items-center rounded-md border border-border px-8 font-semibold hover:bg-secondary"
              >
                Create a free account
              </Link>
            </div>
            <p className="mt-4 text-sm text-muted-foreground">No credit card. Works in Chrome, Edge and Brave.</p>

            <div className="mx-auto mt-14 max-w-5xl overflow-hidden rounded-xl border border-border shadow-2xl shadow-black/60">
              <Image
                src="/screenshots/dashboard.png"
                alt="FocusForge dashboard showing today's focus time, distractions and a weekly chart"
                width={2271}
                height={1331}
                priority
                className="h-auto w-full"
              />
            </div>
          </div>
        </section>

        {/* Features */}
        <section id="features" className="scroll-mt-20 border-t border-border/60">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
            <h2 className="text-center text-3xl font-bold sm:text-4xl">Everything you need to protect your focus</h2>
            <p className="mx-auto mt-4 max-w-2xl text-center text-muted-foreground">
              Simple enough to start in a minute, with the stats and coaching to keep improving.
            </p>
            <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {features.map((f) => (
                <div key={f.title} className="rounded-xl border border-border bg-card p-6">
                  <div className="mb-3 h-1 w-10 rounded-full bg-primary" />
                  <h3 className="text-lg font-semibold">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Showcase */}
        <section className="border-t border-border/60 bg-card/40">
          <div className="mx-auto grid max-w-6xl items-center gap-14 px-4 py-20 sm:px-6 lg:grid-cols-2">
            <div>
              <h2 className="text-3xl font-bold">Focus sessions of any length</h2>
              <p className="mt-4 text-muted-foreground">
                Short sprints or long deep-work blocks. Start from the toolbar, watch the time count down, and get
                a notification when the session ends.
              </p>
            </div>
            <div className="flex justify-center">
              <PopupMockup />
            </div>
          </div>
          <div className="mx-auto grid max-w-6xl items-center gap-14 px-4 pb-20 sm:px-6 lg:grid-cols-2">
            <div className="order-2 flex justify-center lg:order-1">
              <CoachMockup />
            </div>
            <div className="order-1 lg:order-2">
              <h2 className="text-3xl font-bold">A coach that knows your habits</h2>
              <p className="mt-4 text-muted-foreground">
                Ask in plain words. The Focus Coach looks at your real sessions and blocked attempts, answers with
                numbers, and suggests changes. You stay in control: every change waits for your Confirm.
              </p>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how" className="scroll-mt-20 border-t border-border/60">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
            <h2 className="text-center text-3xl font-bold sm:text-4xl">Start in about a minute</h2>
            <div className="mt-12 grid gap-5 md:grid-cols-3">
              {steps.map((s) => (
                <div key={s.n} className="rounded-xl border border-border bg-card p-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary font-bold text-primary-foreground">
                    {s.n}
                  </div>
                  <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{s.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="scroll-mt-20 border-t border-border/60">
          <div className="mx-auto max-w-3xl px-4 py-20 sm:px-6">
            <h2 className="text-center text-3xl font-bold sm:text-4xl">Questions</h2>
            <div className="mt-10 divide-y divide-border rounded-xl border border-border bg-card">
              {faqs.map((f) => (
                <details key={f.q} className="group p-5">
                  <summary className="flex cursor-pointer list-none items-center justify-between font-semibold">
                    {f.q}
                    <span className="ml-4 text-primary transition-transform group-open:rotate-45">+</span>
                  </summary>
                  <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{f.a}</p>
                </details>
              ))}
            </div>
            <p className="mt-6 text-center text-sm text-muted-foreground">
              Curious how it is built?{' '}
              <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                Read the code on GitHub
              </a>
              .
            </p>
          </div>
        </section>

        {/* Final CTA */}
        <section className="border-t border-border/60">
          <div className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6">
            <h2 className="text-3xl font-bold sm:text-4xl">Your next focus session starts here</h2>
            <p className="mt-4 text-muted-foreground">Free to use. Set up in a minute.</p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <a
                href={EXTENSION_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-12 items-center rounded-md bg-primary px-8 font-semibold text-primary-foreground hover:bg-primary/90"
              >
                {EXTENSION_CTA}
              </a>
              <Link
                href="/dashboard"
                className="inline-flex h-12 items-center rounded-md border border-border px-8 font-semibold hover:bg-secondary"
              >
                Open dashboard
              </Link>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
