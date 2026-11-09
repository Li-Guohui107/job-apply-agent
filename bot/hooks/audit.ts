import { defineHook } from "@grok/agent-sdk/hooks";

export default defineHook({
  events: {
    async "action.result"(event, ctx) {
      if (ctx.session.purpose === "eval" || event.data.toolName !== "record_submission") {
        return;
      }
      await ctx.host.kv.put(`audit:${ctx.session.id}:${event.data.callId}`, {
        at: event.at,
        toolName: event.data.toolName,
        isError: event.data.isError,
        stubbed: event.data.stubbed === true,
      });
    },
  },
});
