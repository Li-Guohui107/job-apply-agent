---
description: Use when ranking public job listings against the resume or drafting a tailored application packet.
---

# Job match

A message that starts with `【投递台】` uses `publish_analysis` instead of this skill. Do not call `prepare_application` or `record_submission` for that message.

1. Call `load_profile` and read `resume.md`.
2. If the resume still says `示例候选人`, stop and ask the user to replace it.
3. Call `prepare_application` with the resume text and at most 10 listings.
4. Show the rankings and the draft in Chinese.
5. Call `record_submission` only after the user confirms that exact draft.
