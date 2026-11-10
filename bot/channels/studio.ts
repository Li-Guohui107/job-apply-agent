import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { defineChannel, GET } from "@grok/agent-sdk/channels";
import * as z from "zod/v4";

const pagePath = join(dirname(fileURLToPath(import.meta.url)), "../../web/studio.html");

export default defineChannel({
  routes: [
    GET("/", {
      description: "投递台页面。在本地 dev 打开 /v1/channels/studio。",
      querySchema: z.object({}),
      handler() {
        const html = readFileSync(pagePath, "utf8");
        return new Response(html, {
          headers: {
            "content-type": "text/html; charset=utf-8",
            "cache-control": "no-store",
          },
        });
      },
    }),
  ],
});
