"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export function InquiryForm({ slug }: { slug: string }) {
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  async function submit(form: FormData) {
    setState("sending");
    const { data, error } = await createClient().rpc("submit_inquiry", {
      p_slug: slug, p_name: String(form.get("name") ?? ""), p_contact: String(form.get("contact") ?? ""), p_message: String(form.get("message") ?? ""),
    });
    setState(!error && data ? "sent" : "error");
  }
  if (state === "sent") return <p className="rounded-xl bg-white p-5 text-[15px] shadow-sm">Thank you! Your message was sent.</p>;
  return (
    <form action={submit} className="space-y-3">
      <input name="name" maxLength={80} placeholder="Your name" className="w-full rounded-xl border border-[#D9D5C8] bg-white px-4 py-3 text-[15px]" />
      <input name="contact" maxLength={80} placeholder="Phone or email (so they can reply)" className="w-full rounded-xl border border-[#D9D5C8] bg-white px-4 py-3 text-[15px]" />
      <textarea name="message" required maxLength={1000} rows={4} placeholder="What would you like to know?" className="w-full rounded-xl border border-[#D9D5C8] bg-white px-4 py-3 text-[15px]" />
      <button type="submit" disabled={state === "sending"} className="w-full rounded-xl bg-[#1F2618] px-4 py-3 text-[15px] font-semibold text-[#FCF9F4] disabled:opacity-50">{state === "sending" ? "Sending…" : "Send"}</button>
      {state === "error" && <p role="alert" className="text-[13px] text-red-700">The message could not be sent. Please try again later.</p>}
    </form>
  );
}
