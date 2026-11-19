import { assertEquals, assertRejects } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { chunks, mapWithConcurrency } from "./batches.ts";

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

Deno.test("splits cards into batches of at most ten", () => {
  const batches = chunks(Array.from({ length: 23 }, (_, index) => index), 10);
  assertEquals(batches.map((batch) => batch.length), [10, 10, 3]);
});

Deno.test("runs batches in parallel up to the limit and keeps their order", async () => {
  let running = 0;
  let peak = 0;
  const results = await mapWithConcurrency([30, 5, 20, 1, 10, 2], 3, async (delay, index) => {
    running += 1;
    peak = Math.max(peak, running);
    await wait(delay);
    running -= 1;
    return index;
  });
  assertEquals(results, [0, 1, 2, 3, 4, 5]);
  assertEquals(peak, 3);
});

Deno.test("starts no new batch after a failure and waits for running ones", async () => {
  const started: number[] = [];
  let finished = 0;
  await assertRejects(
    () =>
      mapWithConcurrency([0, 1, 2, 3, 4, 5], 2, async (value) => {
        started.push(value);
        if (value === 0) throw new Error("batch failed");
        await wait(10);
        finished += 1;
        return value;
      }),
    Error,
    "batch failed",
  );
  assertEquals(started, [0, 1]);
  assertEquals(finished, 1);
});
