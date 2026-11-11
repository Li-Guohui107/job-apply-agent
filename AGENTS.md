# job-apply-agent

This repository is a local Python service. The browser page lives in `web/studio.html`. Python under `app/` owns search, the DeepSeek call, and the local record gate.

Folder notes: `app/README.md`, `web/README.md`, `data/README.md`, `tests/README.md`.

## Run

```bash
python -m unittest discover -s tests
python -m app
```

Use Python 3.11 or newer. Do not add a package unless the standard library cannot do the job.

## Do not

- Invent job listings, employers, or resume facts in code. Search results are data. Drop any model URL that was not in the search result.
- Log `DEEPSEEK_API_KEY` or resume text.
- Record a submission unless `confirmed` is true. Do not overwrite an existing job key.
- Sign in to a job site or submit an application form.
