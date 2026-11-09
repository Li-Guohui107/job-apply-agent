import { prompt } from "@grok/agent-sdk";
import { defineTool } from "@grok/agent-sdk/tools";
import * as z from "zod/v4";

export default defineTool({
  description: prompt`
    Record one approved application packet locally.
    Call this only after the user confirms that exact draft.
    Pass confirmed true. This does not submit a form on a job site.
  `,
  effect: "idempotent",
  needsApproval: true,
  inputSchema: z.object({
    jobKey: z.string().trim().min(1).max(180),
    title: z.string().trim().min(1).max(200),
    company: z.string().trim().min(1).max(200),
    location: z.string().trim().min(1).max(80),
    url: z.string().url().max(500),
    packet: z.string().trim().min(1).max(8000),
    confirmed: z.literal(true),
  }),
  dryRunResult: ({ jobKey }) => ({
    recorded: false,
    dryRun: true,
    jobKey: normalizeJobKey(jobKey),
  }),
  async execute(input, ctx) {
    const jobKey = normalizeJobKey(input.jobKey);
    if (ctx.session.purpose === "eval") {
      return { recorded: false, reason: "eval", jobKey };
    }

    const key = `submission:${jobKey}`;
    const existing = await ctx.host.kv.get(key);
    if (existing !== undefined) {
      return { recorded: false, duplicate: true, jobKey };
    }

    await ctx.host.kv.put(key, {
      jobKey,
      title: input.title,
      company: input.company,
      location: input.location,
      url: input.url,
      packet: input.packet,
      recordedAt: new Date().toISOString(),
    });

    return { recorded: true, duplicate: false, jobKey };
  },
});

function normalizeJobKey(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, "-").slice(0, 180);
}
