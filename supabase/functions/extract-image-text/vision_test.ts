import { offlineTest } from "../offline-test-helper.ts";
import { assertEquals, assertRejects, assertThrows } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { readImageText, validateImages } from "./vision.ts";

const png = { id: "0-0", mime: "image/png", data: btoa("\x89PNG fake image") };
const reply = (text: string) =>
  new Response(JSON.stringify({ choices: [{ message: { content: JSON.stringify({ text }) } }] }), { status: 200 });

offlineTest("sends the image as a data URL and returns the transcribed text", async () => {
  let body: Record<string, unknown> | undefined;
  const fakeFetch: typeof fetch = async (_input, init) => {
    body = JSON.parse(String(init?.body));
    return reply("WACC = E/V Re + D/V Rd (1 - T)");
  };
  const text = await readImageText("test-key", "test-model", png, fakeFetch);
  assertEquals(text, "WACC = E/V Re + D/V Rd (1 - T)");
  const content = (body?.messages as Array<{ content: unknown }>)[1].content as Array<Record<string, unknown>>;
  assertEquals((content.find((part) => part.type === "image_url")?.image_url as { url: string }).url, `data:image/png;base64,${png.data}`);
  assertEquals(JSON.stringify(body).includes("test-key"), false);
});

offlineTest("retries one temporary provider failure", async () => {
  let calls = 0;
  const fakeFetch: typeof fetch = async () => {
    calls += 1;
    return calls === 1 ? new Response("busy", { status: 503 }) : reply("Net present value");
  };
  assertEquals(await readImageText("test-key", "test-model", png, fakeFetch), "Net present value");
  assertEquals(calls, 2);
});

offlineTest("reports a lasting provider failure", async () => {
  const fakeFetch: typeof fetch = async () => new Response("bad", { status: 400 });
  await assertRejects(() => readImageText("test-key", "test-model", png, fakeFetch), Error, "could not be read");
});

offlineTest("accepts an empty transcription for images without text", async () => {
  assertEquals(await readImageText("test-key", "test-model", png, async () => reply("   ")), "");
});

offlineTest("validates image count, type, size and ids", () => {
  assertEquals(validateImages({ images: [png] }).length, 1);
  assertThrows(() => validateImages({ images: [] }), Error, "between 1 and 3");
  assertThrows(() => validateImages({ images: [png, png, png, png] }), Error, "between 1 and 3");
  assertThrows(() => validateImages({ images: [{ ...png, mime: "image/svg+xml" }] }), Error, "PNG, JPEG, GIF or WebP");
  assertThrows(() => validateImages({ images: [{ ...png, data: "x".repeat(5_600_001) }] }), Error, "4 MB");
  assertThrows(() => validateImages({ images: [{ ...png, data: "not base64!" }] }), Error, "image data");
  assertThrows(() => validateImages({ images: [png, { ...png }] }), Error, "different");
});
