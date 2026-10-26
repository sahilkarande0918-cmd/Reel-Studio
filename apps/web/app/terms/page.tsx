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
    <h2>AI-generated video</h2>
    <p>&ldquo;Animate my photos&rdquo; turns photos into video with the LTX-Video model (LTXV Open Weights License). Shots made
      this way are machine-generated and must be disclosed as such when published; Reel Studio labels them and adds a
      note to the suggested caption. You may not use this feature to impersonate people without their consent (deepfakes),
      to harm, harass, defame or exploit anyone (including minors), to spread false information, or for any unlawful
      purpose, as set out in Attachment A of that licence.</p>
  </LegalPage>;
}
