import { prompt } from "@grok/agent-sdk";
import { defineTool } from "@grok/agent-sdk/tools";
import * as z from "zod/v4";

export default defineTool({
  description: prompt`
    Read the resume file in the session workspace.
    Default file is resume.md. Use this before prepare_application.
  `,
  execution: "agent",
  inputSchema: z.object({
    file: z.string().trim().min(1).max(80).optional(),
  }),
  script: `#!/usr/bin/env bash
set -euo pipefail
node -e 'const fs=require("fs"); let raw=""; process.stdin.setEncoding("utf8"); process.stdin.on("data",(chunk)=>{raw+=chunk}); process.stdin.on("end",()=>{ let input={}; try { input=JSON.parse(raw||"{}"); } catch { process.stdout.write(JSON.stringify({ok:false,error:"invalid json"})); return; } const file=typeof input.file==="string"&&input.file.length>0?input.file:"resume.md"; if(!/^[A-Za-z0-9._-]+$/.test(file)){ process.stdout.write(JSON.stringify({ok:false,error:"file must stay inside the workspace"})); return; } const found=fs.existsSync(file); const text=found?fs.readFileSync(file,"utf8").slice(0,12000):""; process.stdout.write(JSON.stringify({ok:found,file,chars:text.length,text,sample:text.includes("示例候选人")})); });'
`,
});
