import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
import { requestQuestionsFromRequesty } from "./requesty.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Content-Type": "application/json",
};

const json = (status: number, body: Record<string, unknown>) =>
  new Response(JSON.stringify(body), { status, headers: corsHeaders });

const chunks = <T>(values: T[], size: number): T[][] =>
  Array.from({ length: Math.ceil(values.length / size) }, (_, index) =>
    values.slice(index * size, (index + 1) * size)
  );

serve(async (request) => {
  if (request.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (request.method !== "POST") {
    return json(405, { error: "Use POST to generate questions." });
  }

  const authorization = request.headers.get("Authorization");
  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const supabaseAnonKey = Deno.env.get("SUPABASE_ANON_KEY");
  const requestyApiKey = Deno.env.get("REQUESTY_API_KEY");
  const requestyModel = Deno.env.get("REQUESTY_MODEL") ?? "openai/gpt-4o-mini";

  if (!authorization || !supabaseUrl || !supabaseAnonKey) {
    return json(401, { error: "Sign in before generating questions." });
  }
  if (!requestyApiKey) {
    return json(503, { error: "AI generation is not configured yet." });
  }

  let input: { importId?: unknown; cardIds?: unknown };
  try {
    input = await request.json();
  } catch {
    return json(400, { error: "Send a JSON request with an import and selected cards." });
  }

  if (
    typeof input.importId !== "string" ||
    !Array.isArray(input.cardIds) ||
    input.cardIds.length < 1 ||
    input.cardIds.length > 100 ||
    input.cardIds.some((id) => typeof id !== "string") ||
    new Set(input.cardIds).size !== input.cardIds.length
  ) {
    return json(400, { error: "Select between 1 and 100 different source cards." });
  }
  const cardIds = input.cardIds as string[];

  const supabase = createClient(supabaseUrl, supabaseAnonKey, {
    global: { headers: { Authorization: authorization } },
  });

  const { data: userResult, error: userError } = await supabase.auth.getUser();
  if (userError || !userResult.user) {
    return json(401, { error: "Your session has expired. Sign in and try again." });
  }

  const { data: cards, error: cardsError } = await supabase
    .from("anki_source_cards")
    .select("id, import_id, front, back, position")
    .eq("import_id", input.importId)
    .in("id", cardIds)
    .order("position");

  if (cardsError || !cards || cards.length !== cardIds.length) {
    return json(403, { error: "One or more selected source cards are unavailable." });
  }

  const { data: locked, error: lockError } = await supabase.rpc("claim_ai_generation_lock");
  if (lockError) {
    return json(500, { error: "Could not start question generation. Try again." });
  }
  if (!locked) {
    return json(409, { error: "Question generation is already running. Please wait for it to finish." });
  }

  try {
    const drafts = [];
    for (const batch of chunks(cards, 10)) {
      const generated = await requestQuestionsFromRequesty(
        requestyApiKey,
        requestyModel,
        batch.map(({ id, front, back }) => ({ id, front, back })),
      );
      drafts.push(...generated);
    }

    const { data: saved, error: saveError } = await supabase.rpc("save_ai_question_drafts", {
      p_import_id: input.importId,
      p_drafts: drafts,
    });
    if (saveError || !saved) {
      return json(500, { error: "The generated drafts could not be saved. No drafts were created." });
    }
    return json(200, { count: saved.count, status: "draft" });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Question generation failed.";
    return json(502, { error: message });
  } finally {
    await supabase.rpc("release_ai_generation_lock");
  }
});
