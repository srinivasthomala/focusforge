import { SiteFooter, SiteHeader } from '@/components/SiteChrome';
import { CONTACT_EMAIL, ISSUES_URL } from '@/lib/site';

export function LegalPage({ title, updated, children }: { title: string; updated: string; children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <h1 className="text-4xl font-bold">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">Last updated {updated}</p>
        <div className="legal mt-10 space-y-4 leading-relaxed text-foreground/90 [&_a]:text-primary [&_a:hover]:underline [&_h2]:mt-10 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-foreground [&_li]:ml-5 [&_li]:list-disc [&_li]:pl-1 [&_ul]:space-y-2">
          {children}
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}

export function Contact() {
  return CONTACT_EMAIL ? (
    <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
  ) : (
    <a href={ISSUES_URL} target="_blank" rel="noopener noreferrer">
      GitHub issues
    </a>
  );
}
