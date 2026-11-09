import { defineAgent } from "@grok/agent-sdk";

export default defineAgent({
  name: "job-apply-agent",
  description:
    "Searches public computer, Agent-development, and algorithm jobs, then prepares an application packet.",
  model: {
    id: "grok-4.7",
    params: [
      { id: "reasoning_effort", value: "high" },
      { id: "fast", value: "true" },
    ],
  },
  hosting: {
    egressDomains: ["api.deepseek.com"],
    secretNames: ["DEEPSEEK_API_KEY"],
  },
});
