/** Surface validation messages without copying request inputs (OAuth codes can be among them). */
export function apiErrorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail.flatMap((item) => {
        if (!item || typeof item !== "object" || typeof item.msg !== "string") return [];
        // e.g. ["body","storyboard","scenes",1] → "Scene 2"; other fields keep their name
        const loc = Array.isArray(item.loc) ? item.loc.filter((part: unknown) => part !== "body") : [];
        const scene = loc.indexOf("scenes");
        const field = scene >= 0 && typeof loc[scene + 1] === "number" ? `Scene ${loc[scene + 1] + 1}` : loc.filter((part: unknown) => typeof part === "string").join(" · ");
        return [field ? `${field}: ${item.msg.replace(/^Value error, /, "")}` : item.msg];
      });
      if (messages.length) return messages.join(". ");
    }
  }
  return `The request failed (${status}). Please try again.`;
}
