import { prompt } from "@grok/agent-sdk";
import { defineTool } from "@grok/agent-sdk/tools";
import * as z from "zod/v4";

const Listing = z.object({
  title: z.string().trim().min(1).max(200),
  company: z.string().trim().min(1).max(200),
  location: z.string().trim().min(1).max(80),
  url: z.string().url().max(500),
  summary: z.string().trim().min(1).max(2000),
});

type Ranking = {
  url: string;
  score: number;
  reason: string;
};

type Draft = {
  subject: string;
  body: string;
  listingUrl: string;
};

const SYSTEM = prompt`
  You rank public job listings against a resume and draft one Chinese application.
  Use only facts that appear in the resume. Do not invent employers, degrees, dates, or metrics.
  Return one JSON object with this shape:
  {"rankings":[{"url":"","score":0,"reason":""}],"draft":{"subject":"","body":"","listingUrl":""}}
  Score each listing from 0 to 100. The draft is for the highest-scoring listing.
  The draft is text the user can paste. It is not a claim that the job was submitted.
`;

export default defineTool({
  description: prompt`
    Rank listings against the resume and draft one application packet.
    This calls the DeepSeek API. It does not submit the application.
  `,
  effect: "read",
  inputSchema: z.object({
    resumeText: z.string().trim().min(1).max(12000),
    listings: z.array(Listing).min(1).max(10),
  }),
  async execute({ resumeText, listings }) {
    const apiKey = process.env.DEEPSEEK_API_KEY;
    if (apiKey === undefined || apiKey.trim() === "") {
      return {
        ok: false as const,
        error: "DEEPSEEK_API_KEY is not set",
      };
    }

    const model = process.env.DEEPSEEK_MODEL?.trim() || "deepseek-chat";
    let response: Response;
    try {
      response = await fetch("https://api.deepseek.com/chat/completions", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          temperature: 0.2,
          response_format: { type: "json_object" },
          messages: [
            { role: "system", content: SYSTEM },
            {
              role: "user",
              content: JSON.stringify({ resumeText, listings }),
            },
          ],
        }),
        signal: AbortSignal.timeout(45_000),
      });
    } catch (error) {
      return {
        ok: false as const,
        error: error instanceof Error ? error.message : "DeepSeek request failed",
      };
    }

    if (!response.ok) {
      return {
        ok: false as const,
        error: `DeepSeek HTTP ${response.status}`,
      };
    }

    const payload = (await response.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
    };
    const content = payload.choices?.[0]?.message?.content ?? "";
    let parsed: unknown;
    try {
      parsed = JSON.parse(content);
    } catch {
      return {
        ok: false as const,
        error: "DeepSeek returned non-JSON",
        raw: content.slice(0, 500),
      };
    }

    return {
      ok: true as const,
      model,
      rankings: readRankings(parsed),
      draft: readDraft(parsed),
    };
  },
});

function readRankings(value: unknown): Ranking[] {
  if (typeof value !== "object" || value === null || !("rankings" in value)) {
    return [];
  }
  const rankings = value.rankings;
  if (!Array.isArray(rankings)) {
    return [];
  }
  return rankings.flatMap((item) => {
    if (typeof item !== "object" || item === null) {
      return [];
    }
    const url = "url" in item && typeof item.url === "string" ? item.url : "";
    const reason = "reason" in item && typeof item.reason === "string" ? item.reason : "";
    const score = "score" in item && typeof item.score === "number" ? item.score : 0;
    if (url === "") {
      return [];
    }
    return [{ url, reason: reason.slice(0, 400), score: Math.max(0, Math.min(100, score)) }];
  });
}

function readDraft(value: unknown): Draft {
  const empty = { subject: "", body: "", listingUrl: "" };
  if (typeof value !== "object" || value === null || !("draft" in value)) {
    return empty;
  }
  const draft = value.draft;
  if (typeof draft !== "object" || draft === null) {
    return empty;
  }
  return {
    subject: "subject" in draft && typeof draft.subject === "string" ? draft.subject.slice(0, 120) : "",
    body: "body" in draft && typeof draft.body === "string" ? draft.body.slice(0, 4000) : "",
    listingUrl:
      "listingUrl" in draft && typeof draft.listingUrl === "string" ? draft.listingUrl.slice(0, 500) : "",
  };
}
