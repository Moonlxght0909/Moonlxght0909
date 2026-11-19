# Setup — Moonlxght0909 Daily AI Profile

This kit contains a profile `README.md` and a GitHub Actions workflow that refreshes it every day.

## 1. Create the profile repository

Create a **public** repository named exactly:

`Moonlxght0909`

The repository name must match your GitHub username for GitHub to display its README on your profile.

## 2. Upload these files

Upload the contents of this kit to the root of that repository, preserving this structure:

```text
.
├── README.md
├── scripts/
│   └── update_profile.py
└── .github/
    └── workflows/
        └── daily-profile.yml
```

## 3. Add the OpenAI API key

In the repository, open:

`Settings → Secrets and variables → Actions → New repository secret`

Create a secret named:

`OPENAI_API_KEY`

Set its value to your OpenAI API key. The workflow uses the OpenAI Responses API and the model configured in the workflow (`gpt-4.1-mini`). API usage is billed separately from a ChatGPT subscription.

Do not put the API key directly in README, Python files, or workflow YAML.

## 4. Enable Actions write permission

Open:

`Settings → Actions → General → Workflow permissions`

Allow **Read and write permissions**, then save.

The workflow also declares `contents: write` so it can commit the refreshed README.

## 5. Run the first update

Open:

`Actions → Daily GitHub Profile Update → Run workflow`

The schedule is daily at **00:00 UTC (07:00 WIB)**. GitHub may delay scheduled jobs during high load. The workflow can also be run manually.

## What updates daily?

- Public, non-fork repositories are fetched from the GitHub API and displayed as repository highlights.
- Recent public commit metadata is provided to the AI to create a short daily developer brief.
- The workflow commits `README.md` only when its contents have changed.

## AI and privacy notes

- The AI brief is generated from public repository metadata and public commit messages only.
- The script does not intentionally send repository source code or private repository contents to the AI.
- If `OPENAI_API_KEY` is missing, the README displays a setup notice instead of claiming that AI ran.
- The OpenAI API key is a separate API credential; ChatGPT Plus/Free access does not automatically include API credits.
