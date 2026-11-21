type FetchLike = typeof fetch;
export type CardImage = { id: string; mime: string; data: string };

const TYPES = new Set(["image/png", "image/jpeg", "image/gif", "image/webp"]);
// 4 MB of image data is about 5.6 million base64 characters.
const MAX_BASE64 = 5_600_000;
const MAX_IMAGES = 3;
const BASE64 = /^[A-Za-z0-9+/]+={0,2}$/;

const PROMPT = [
  "You read the text on images from students' study flashcards.",
  "Transcribe all readable text exactly as written, in its original language, keeping formulas, numbers and list order.",
  "Write formulas in plain text. Do not describe pictures, add explanations, translate or summarise.",
  "If the image contains no readable text, return an empty string.",
  "Return only JSON of the form {\"text\": \"...\"}.",
].join(" ");

const TEXT_SCHEMA = {
  type: "json_schema",
  json_schema: {
    name: "image_text",
    strict: true,
    schema: { type: "object", additionalProperties: false, required: ["text"], properties: { text: { type: "string" } } },
  },
};

/** Validate the request body; one card sends at most three images. */
export function validateImages(input: unknown): CardImage[] {
  const images = (input as { images?: unknown })?.images;
  if (!Array.isArray(images) || images.length < 1 || images.length > MAX_IMAGES) {
    throw new Error("Send between 1 and 3 images of one card.");
  }
  const seen = new Set<string>();
  return images.map((image) => {
    const { id, mime, data } = (image ?? {}) as Record<string, unknown>;
    if (typeof id !== "string" || !id || id.length > 40 || seen.has(id)) throw new Error("Each image needs a different id.");
    seen.add(id);
    if (typeof mime !== "string" || !TYPES.has(mime)) throw new Error("Only PNG, JPEG, GIF or WebP images can be read.");
    if (typeof data !== "string") throw new Error("The image data is missing.");
    if (data.length > MAX_BASE64) throw new Error("Each image must be smaller than 4 MB.");
    if (!BASE64.test(data)) throw new Error("The image data is not valid base64.");
    return { id, mime, data };
  });
}

/** Transcribe the text on one image with a vision model through Requesty. Retries one temporary failure. */
export async function readImageText(apiKey: string, model: string, image: CardImage, fetcher: FetchLike): Promise<string> {
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 45_000);
    const started = Date.now();
    try {
      const response = await fetcher("https://router.requesty.ai/v1/chat/completions", {
        method: "POST",
        headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          model,
          response_format: TEXT_SCHEMA,
          messages: [
            { role: "system", content: PROMPT },
            {
              role: "user",
              content: [
                { type: "text", text: "Transcribe the text on this flashcard image." },
                { type: "image_url", image_url: { url: `data:${image.mime};base64,${image.data}` } },
              ],
            },
          ],
        }),
        signal: controller.signal,
      });
      if ((response.status === 429 || response.status >= 500) && attempt === 1) continue;
      if (!response.ok) throw new Error(`The image could not be read (HTTP ${response.status}). Try a clearer image or type the text yourself.`);
      const body = await response.json() as { choices?: Array<{ message?: { content?: unknown } }>; usage?: { prompt_tokens?: number; completion_tokens?: number } };
      // Metrics only: never log image data or the transcribed text.
      console.log("Requesty image text", { model, ms: Date.now() - started, promptTokens: body?.usage?.prompt_tokens, completionTokens: body?.usage?.completion_tokens });
      const content = body?.choices?.[0]?.message?.content;
      if (typeof content !== "string") throw new Error("The image could not be read. Try again.");
      let text: unknown;
      try {
        text = JSON.parse(content.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "")).text;
      } catch {
        throw new Error("The image could not be read. Try again.");
      }
      if (typeof text !== "string") throw new Error("The image could not be read. Try again.");
      return text.trim();
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        if (attempt === 1) continue;
        throw new Error("Reading the image took too long. Try again.");
      }
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }
  throw new Error("The image could not be read. Try again later.");
}
