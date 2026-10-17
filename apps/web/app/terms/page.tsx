import { LegalPage } from "@/components/landing/legal-page";

export const metadata = { title: "Terms — Reel Studio" };

export default function Terms() {
  return <LegalPage title="Terms" updated="17 October 2026">
    <p>Reel Studio is provided free, as is, as an open-source hackathon project under the MIT licence.</p>
    <h2>Your content</h2>
    <p>You keep all rights to the recordings and ideas you bring. Only upload content you have the right to use and to publish.</p>
    <h2>Publishing</h2>
    <p>You are responsible for what you publish to connected accounts and for following Instagram&apos;s terms and community guidelines.</p>
    <h2>Availability</h2>
    <p>Processing depends on the workspace&apos;s own machine being online. There is no guarantee of uptime, and features may change.</p>
    <h2>AI output</h2>
    <p>Transcripts, highlights, scripts and code examples are generated automatically. Review them before publishing.</p>
  </LegalPage>;
}
