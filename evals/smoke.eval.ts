import { defineEval, includes } from "@grok/agent-sdk/evals";

export default defineEval({
  tags: ["smoke"],
  description: "A city search calls search_jobs and does not record a submission.",
  async test(t) {
    await t.send("搜索上海的 Agent 开发岗位。先调用 search_jobs。不要记录投递。");
    t.succeeded();
    t.calledTool("search_jobs");
    t.notCalledTool("record_submission");
    t.check(t.reply, includes(/上海|Agent|岗位/));
  },
});
