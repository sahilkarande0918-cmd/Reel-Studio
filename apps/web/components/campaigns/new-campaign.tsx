"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiErrorMessage, apiFetch, useBackend } from "@/lib/backend";

const FIELDS: [string, string, string, boolean][] = [
  ["name", "Business name", "Kicks Corner", true], ["industry", "Industry", "Sneaker store", true], ["city", "City / area", "Kothrud, Pune", false],
  ["audience", "Who are the customers?", "College students who want trendy sneakers", true], ["offer", "Current offer (exact wording, optional)", "10% off during Diwali week", false],
  ["whatsapp", "WhatsApp number (optional)", "+919876543210", false], ["website", "Website (https, optional)", "https://example.com", false],
  ["footage", "Footage or photos you already have", "Shelf shots, try-on videos, the shop front", false],
];

export function NewCampaign({ orgId }: { orgId: string }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(form: FormData) {
    if (!base) return setError("The processing machine is offline.");
    setBusy(true); setError(null);
    const business = Object.fromEntries(FIELDS.map(([k]) => [k, String(form.get(k) ?? "").trim()]));
    const r = await apiFetch(base, "/campaigns", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ org_id: orgId, language: form.get("language"), business: { ...business, goal: form.get("goal") } }) });
    const body = await r.json().catch(() => null);
    setBusy(false);
    if (!r.ok) return setError(apiErrorMessage(body, r.status));
    router.push(`/campaigns/${body.campaign_id}`);
  }
  return (
    <form action={submit} className="studio-panel grid gap-4 p-5 sm:grid-cols-2">
      {FIELDS.map(([k, label, ph, req]) => <label key={k} className="studio-label">{label}<input name={k} required={req} placeholder={ph} className="studio-input" maxLength={k === "audience" || k === "footage" ? 300 : 200} /></label>)}
      <label className="studio-label">Goal<select name="goal" className="studio-input" defaultValue="leads">
        <option value="leads">More enquiries</option><option value="footfall">More walk-ins</option><option value="sales">More sales</option>
        <option value="awareness">Get known locally</option><option value="followers">More followers</option></select></label>
      <label className="studio-label">Language<select name="language" className="studio-input" defaultValue="en">
        <option value="en">English</option><option value="hinglish">Hinglish</option><option value="hi">Hindi</option>
        <option value="mr" disabled>Marathi (not yet: model output not validated)</option></select></label>
      <div className="sm:col-span-2 flex items-center gap-3"><button type="submit" className="studio-button" disabled={busy || !base}>{busy ? "Starting…" : "Plan the campaign"}</button>
        {!base && <span className="text-[12px] text-danger">The processing machine is offline.</span>}{error && <span role="alert" className="text-[12px] text-danger">{error}</span>}</div>
    </form>
  );
}
