"use client";

import { useActionState } from "react";
import { FormMessage, Submit } from "@/components/ui/form";
import { createProject } from "./actions";

export function NewProjectForm({ mode = "recording", fixedMode }: { mode?: "recording" | "edit"; fixedMode?: boolean }) {
  const [state, action] = useActionState(createProject, undefined);
  return (
    <form id="new-project" action={action} className="studio-panel grid scroll-mt-20 gap-4 p-5 lg:grid-cols-[minmax(0,1fr)_220px_auto] lg:items-end">
      <label className="studio-label">New project name
        <input name="name" required maxLength={120} placeholder={mode === "edit" ? "Sneaker drop — phonk reel" : "React hooks — class 7"} className="studio-input" />
      </label>
      {fixedMode ? <input type="hidden" name="mode" value={mode} /> : <label className="studio-label">Type
        <select name="mode" defaultValue={mode} className="studio-input">
          <option value="recording">Recording → Reels</option>
          <option value="edit">Prompt → Edit</option>
        </select>
      </label>}
      <div><Submit>Create project</Submit></div>
      <div className="lg:col-span-3 empty:hidden"><FormMessage state={state} /></div>
    </form>
  );
}
