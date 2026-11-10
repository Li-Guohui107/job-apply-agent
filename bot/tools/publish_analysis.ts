import { prompt } from "@grok/agent-sdk";
import { defineTool } from "@grok/agent-sdk/tools";
import * as z from "zod/v4";

const Track = z.enum(["computer", "agent", "algorithm"]);

const Listing = z.object({
  title: z.string().trim().min(1).max(200),
  company: z.string().trim().min(1).max(200),
  location: z.string().trim().min(1).max(80),
  url: z.string().url().max(500),
  track: Track,
  summary: z.string().trim().min(1).max(400),
  fitScore: z.number().min(0).max(100),
  fitReason: z.string().trim().min(1).max(300),
  gaps: z.array(z.string().trim().min(1).max(120)).max(4),
});

const PlanItem = z.object({
  when: z.string().trim().min(1).max(20),
  title: z.string().trim().min(1).max(80),
  actions: z.array(z.string().trim().min(1).max(160)).min(1).max(4),
});

export default defineTool({
  description: prompt`
    Publish the studio board: public listings, a fit estimate, resume gaps,
    and a preparation plan. Fit scores are not offer probabilities.
    Call this for a 【投递台】 request. Do not submit an application.
  `,
  effect: "read",
  inputSchema: z.object({
    cities: z.array(z.string().trim().min(1).max(40)).min(1).max(8),
    tracks: z.array(Track).min(1).max(3),
    headline: z.string().trim().min(1).max(80),
    overview: z.string().trim().min(1).max(700),
    fitScore: z.number().min(0).max(100),
    confidence: z.enum(["low", "medium", "high"]),
    successRead: z.string().trim().min(1).max(500),
    listings: z.array(Listing).max(8),
    strengths: z.array(z.string().trim().min(1).max(160)).max(5),
    gaps: z.array(z.string().trim().min(1).max(160)).max(6),
    plan: z.array(PlanItem).min(2).max(4),
    draftSubject: z.string().trim().max(120).optional(),
    draftBody: z.string().trim().max(4000).optional(),
  }),
  async execute(input) {
    const listings = input.listings.map((listing) => ({
      title: listing.title,
      company: listing.company,
      location: listing.location,
      url: listing.url,
      track: listing.track,
      summary: listing.summary,
      fitScore: clampScore(listing.fitScore),
      fitReason: listing.fitReason,
      gaps: listing.gaps,
    }));

    return {
      ok: true as const,
      kind: "studio-analysis" as const,
      cities: input.cities,
      tracks: input.tracks,
      headline: input.headline,
      overview: input.overview,
      fitScore: clampScore(input.fitScore),
      confidence: input.confidence,
      successRead: input.successRead,
      listings,
      strengths: input.strengths,
      gaps: input.gaps,
      plan: input.plan,
      draftSubject: input.draftSubject ?? "",
      draftBody: input.draftBody ?? "",
    };
  },
});

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}
