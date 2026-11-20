import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
import { readImageText, validateImages } from "./vision.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Content-Type": "application/json",
};
const json = (status: number, body: Record<string, unknown>) => new Response(JSON.stringify(body), { status, headers: corsHeaders });

/** Reads the text on the images of one Anki card. Nothing is stored; the student reviews the text before importing. */
serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (request.method !== "POST") return json(405, { error: "Use POST to read image text." });

  const authorization = request.headers.get("Authorization");
  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const supabaseAnonKey = Deno.env.get("SUPABASE_ANON_KEY");
  const requestyApiKey = Deno.env.get("REQUESTY_API_KEY");
  const model = Deno.env.get("REQUESTY_VISION_MODEL") ?? "openai/gpt-4o-mini";
  if (!authorization || !supabaseUrl || !supabaseAnonKey) return json(401, { error: "Sign in before reading image text." });
  if (!requestyApiKey) return json(503, { error: "Reading image text is not configured yet." });

  const supabase = createClient(supabaseUrl, supabaseAnonKey, { global: { headers: { Authorization: authorization } } });
  const { data: userResult, error: userError } = await supabase.auth.getUser();
  if (userError || !userResult.user) return json(401, { error: "Your session has expired. Sign in and try again." });

  let images;
  try {
    images = validateImages(await request.json());
  } catch (error) {
    return json(400, { error: error instanceof Error ? error.message : "Send the images of one card." });
  }
  try {
    const texts = await Promise.all(images.map(async (image) => ({ id: image.id, text: await readImageText(requestyApiKey, model, image) })));
    return json(200, { texts });
  } catch (error) {
    const message = error instanceof Error ? error.message : "The image could not be read.";
    console.error("Image text failed", { message });
    return json(502, { error: message });
  }
});
