import { defineConnection } from "@grok/agent-sdk/connections";

export default defineConnection({
  description: "Cursor account connectors the operator already authorized.",
  cursorAccount: true,
  advertiseTools: true,
  optional: true,
});
