import { redirect } from "next/navigation";

/** Topic → Video was replaced by Prompt → Edit (Reel Studio 2.0). Earlier topic projects stay in the library. */
export default function TopicsPage() {
  redirect("/projects?mode=topic");
}
