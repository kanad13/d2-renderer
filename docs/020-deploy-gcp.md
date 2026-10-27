# Deploy to Google Cloud Run

Runbook for a fresh Google Cloud account. After the one-time setup, every push to `main` deploys automatically.

If an agent is following this: ask the user for each value in the table below before running anything, and show each command's effect before it changes their account.

## Values to gather

| Placeholder            | Meaning                                                                                                                                 | How to find it                                                        |
| :--------------------- | :-------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------- |
| `<PROJECT_ID>`         | New Google Cloud project ID, globally unique, for example `d2-renderer-<random>`                                                        | You choose it                                                         |
| `<BILLING_ACCOUNT_ID>` | An **open** billing account to attach                                                                                                   | `gcloud billing accounts list`                                        |
| `<GITHUB_REPO>`        | `<owner>/<repo>` that may deploy                                                                                                        | Your fork's address on GitHub                                         |
| `<REGION>`             | Cloud Run region. Use a Tier 1 EU region so the free tier applies fully (see [operations](./030-operations.md)). Default `europe-west1` | Your data-location needs                                              |
| `<BUDGET_AMOUNT>`      | Alert threshold in the billing account's currency, for example `5USD`                                                                   | Currency from `gcloud billing accounts describe <BILLING_ACCOUNT_ID>` |

## Prerequisites

- A Google account with a billing account and permission to create projects.
- The [`gcloud` CLI](https://cloud.google.com/sdk/docs/install), or open **Cloud Shell** in the Google Cloud console, which has it already. Cloud Shell is the simplest route on a machine you do not own.
- The [`gh` CLI](https://cli.github.com), signed in as someone who can edit the repository's settings. Or use the GitHub web UI for step 4.
- The container image must be public on GitHub Container Registry so Cloud Run can pull it without credentials. See [decision 040](./decisions/040-public-image-pulled-directly.md).

## 1. Sign in

```bash
gcloud auth login
```

## 2. Run the setup script

Why: creates everything the deploy needs and nothing more: project, billing link, APIs, a deploy identity, a no-permission runtime identity, GitHub-to-Google trust limited to one repository's `main` branch, and a budget alert. See [decision 030](./decisions/030-keyless-github-deploy.md).

```bash
PROJECT_ID=<PROJECT_ID> \
BILLING_ACCOUNT_ID=<BILLING_ACCOUNT_ID> \
GITHUB_REPO=<GITHUB_REPO> \
REGION=<REGION> \
BUDGET_AMOUNT=<BUDGET_AMOUNT> \
./scripts/gcp-setup.sh
```

The script is safe to re-run. It ends by printing five `NAME=value` lines for step 3.

## 3. Save the printed values as GitHub variables

Why: the workflow reads them, so no account detail lives in the repository. They are identifiers, not secrets.

```bash
gh variable set GCP_PROJECT_ID -R <GITHUB_REPO> -b "<value printed by the script>"
gh variable set GCP_REGION -R <GITHUB_REPO> -b "<value printed by the script>"
gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER -R <GITHUB_REPO> -b "<value printed by the script>"
gh variable set GCP_DEPLOYER_SERVICE_ACCOUNT -R <GITHUB_REPO> -b "<value printed by the script>"
gh variable set GCP_RUNTIME_SERVICE_ACCOUNT -R <GITHUB_REPO> -b "<value printed by the script>"
```

Web UI alternative: repository **Settings > Secrets and variables > Actions > Variables**.

## 4. Deploy

Why: pushing proves the whole chain (test, publish, authenticate, deploy) in one step.

Push any commit to `main`, or re-run the latest workflow. Watch it:

```bash
gh run list -R <GITHUB_REPO> -L 1
```

The `Deploy to Cloud Run` job is skipped until `GCP_PROJECT_ID` exists, so forks stay green until configured.

## 5. Verify

Find the service address:

```bash
gcloud run services describe d2-renderer --project=<PROJECT_ID> --region=<REGION> --format='value(status.url)'
```

Then run the visual check against it:

```bash
RENDERER_REMOTE_URL=<SERVICE_URL> python3 scripts/build-render-check.py
```

Open `render-check/index.html` (serve it with `python3 -m http.server -d render-check`) and confirm every diagram appears in both columns.

## Troubleshooting

| Symptom                                                                     | Cause                                                                                    | Fix                                                                 |
| :-------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------- | :------------------------------------------------------------------ |
| `PERMISSION_DENIED` creating the identity pool right after project creation | New APIs need up to a minute to accept IAM calls                                         | Wait, then re-run the script                                        |
| Budget step says the API needs a quota project                              | Budgets API rejects calls without one                                                    | The script passes `--billing-project`; use the current script       |
| Budget step rejects the amount                                              | Currency suffix differs from the billing account                                         | Use the account's currency, for example `400INR`                    |
| Deploy job fails at authentication                                          | Branch is not `main`, repository name differs from `<GITHUB_REPO>`, or variables missing | Re-run setup with the right `GITHUB_REPO`; check `gh variable list` |
| Deploy fails making the service public                                      | An organization policy blocks public access                                              | Ask the organization admin to allow it for this project             |
| Cloud Run cannot pull the image                                             | The package is private                                                                   | Make the GHCR package public                                        |

## Navigation

- [Documentation index](./README.md)
- Previous: [Architecture](./010-architecture.md) · Next: [Operations](./030-operations.md)
