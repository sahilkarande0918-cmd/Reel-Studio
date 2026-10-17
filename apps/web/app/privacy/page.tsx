import { LegalPage } from "@/components/landing/legal-page";

export const metadata = { title: "Privacy — Reel Studio" };

export default function Privacy() {
  return <LegalPage title="Privacy" updated="17 October 2026">
    <p>Reel Studio is a student hackathon project. This page explains what it stores and why.</p>
    <h2>What we store</h2>
    <p>Your account email and workspace data (projects, transcripts, highlights, brand kits, timelines and publishing records) are stored in our Supabase database, protected by row-level security so only members of a workspace can read it.</p>
    <h2>Your videos</h2>
    <p>Recordings, generated audio and rendered videos are processed and stored on the workspace&apos;s own processing machine, not in a third-party cloud. Transcription, AI generation and rendering run locally on that machine.</p>
    <h2>Instagram</h2>
    <p>If you connect an Instagram Business or Creator account, we store its access token encrypted at rest and use it only to publish posts you approve and to read their insights. You can disconnect at any time from the Publish page, which deletes the stored token.</p>
    <h2>Sharing</h2>
    <p>We do not sell or share your data. Content is published to Instagram only when you choose to publish it.</p>
    <h2>Contact</h2>
    <p>Questions or deletion requests: open an issue on our <a className="underline" href="https://github.com/sahilkarande0918-cmd/Reel-Studio">GitHub repository</a>.</p>
  </LegalPage>;
}
