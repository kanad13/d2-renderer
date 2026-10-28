# Deploy to Google Cloud Run

Runbook for setting up and deploying an on-demand instance of the service to Google Cloud Run.

- **Audience & Scope:**
  - Designed for maintainers or fork authors establishing their own cloud deployment.
  - Forks and clones cannot deploy to another maintainer's project due to cryptographic OIDC federation boundaries.
  - Running a local container requires none of this setup; see [Run locally](./010-run-locally.md).
- **Deployment Model:**
  - GitHub Actions runs tests and publishes container images to GHCR on every push to `main`.
  - Cloud Run deployments run on demand via manual workflow dispatch (`gh workflow run ci.yml`).
  - Deployments configure `--no-allow-unauthenticated` by default to prevent accidental public exposure.
  - Public access is controlled on demand using the 1-command IAM toggle in [Operations](./050-operations.md#bring-the-service-online-and-take-it-offline).

## Values to gather

| Placeholder            | Meaning                                                                                                                                 | How to find it                                                        |
| :--------------------- | :-------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------- |
| `<PROJECT_ID>`         | New Google Cloud project ID, globally unique, for example `d2-renderer-<random>`                                                        | You choose it                                                         |
| `<BILLING_ACCOUNT_ID>` | An **open** billing account to attach                                                                                                   | `gcloud billing accounts list`                                        |
| `<GITHUB_REPO>`        | `<owner>/<repo>` authorized to deploy                                                                                                   | Your repository address on GitHub                                     |
| `<REGION>`             | Cloud Run region. Use a Tier 1 EU region so the free tier applies fully (see [operations](./050-operations.md)). Default `europe-west1` | Your data-location needs                                              |
| `<BUDGET_AMOUNT>`      | Alert threshold in the billing account's currency, for example `5USD`                                                                   | Currency from `gcloud billing accounts describe <BILLING_ACCOUNT_ID>` |

## Prerequisites

- **Required Access & Tools:**
  - A Google Cloud account with an active billing account and project creation permissions.
  - The [`gcloud` CLI](https://cloud.google.com/sdk/docs/install) installed locally or Google Cloud Shell.
  - The [`gh` CLI](https://cli.github.com) signed in with administrative access to `<GITHUB_REPO>`.
  - A public GitHub Container Registry package so Cloud Run can pull images without credentials ([decision 040](./decisions/040-public-image-pulled-directly.md)).

## 1. Sign in

- **Authentication:**
  - Authenticate your local shell to Google Cloud before running deployment commands.

```bash
gcloud auth login
```

## 2. Run the setup script

- **Automated Provisioning:**
  - Sets up the project, links billing, enables required APIs, and provisions keyless OIDC trust ([decision 030](./decisions/030-keyless-github-deploy.md)).
  - Creates a dedicated deployer service account and a zero-permission runtime service account.
  - Configures a budget alert threshold to guard against unexpected usage ([decision 050](./decisions/050-traffic-limits-and-cost-guardrails.md)).

```bash
PROJECT_ID=<PROJECT_ID> \
BILLING_ACCOUNT_ID=<BILLING_ACCOUNT_ID> \
GITHUB_REPO=<GITHUB_REPO> \
REGION=<REGION> \
BUDGET_AMOUNT=<BUDGET_AMOUNT> \
./scripts/gcp-setup.sh
```

- **Output:**
  - The script prints five `NAME=value` lines required for GitHub Actions repository variables.

## 3. Save the printed values as GitHub variables

- **Configuration Storage:**
  - Sets non-secret repository variables so workflows authenticate keylessly via workload identity federation.

```bash
gh variable set GCP_PROJECT_ID -R <GITHUB_REPO> -b "<value printed by the script>"
gh variable set GCP_REGION -R <GITHUB_REPO> -b "<value printed by the script>"
gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER -R <GITHUB_REPO> -b "<value printed by the script>"
gh variable set GCP_DEPLOYER_SERVICE_ACCOUNT -R <GITHUB_REPO> -b "<value printed by the script>"
gh variable set GCP_RUNTIME_SERVICE_ACCOUNT -R <GITHUB_REPO> -b "<value printed by the script>"
```

- **Web UI Alternative:**
  - Navigate to repository **Settings > Secrets and variables > Actions > Variables**.

## 4. Deploy

- **Execution:**
  - Trigger the GitHub Actions deploy job explicitly ([decision 090](./decisions/090-on-demand-cloud-run-deployment.md)).
  - The workflow builds and publishes the image, authenticates keylessly to GCP, and provisions the Cloud Run revision.

```bash
gh workflow run ci.yml -R <GITHUB_REPO>
```

- **Safety Guarantee:**
  - Everyday pushes to `main` test and publish images but do not deploy to Cloud Run automatically.
  - The deploy job runs only when explicitly dispatched and requires `GCP_PROJECT_ID` to exist.

## 5. Verify

- **Address Resolution:**
  - Retrieve the deployed service URL from Cloud Run metadata.

```bash
gcloud run services describe d2-renderer --project=<PROJECT_ID> --region=<REGION> --format='value(status.url)'
```

- **Visual Verification:**
  - Generate the comparison check page to ensure diagrams render identically to the local container.

```bash
RENDERER_REMOTE_URL=<SERVICE_URL> python3 scripts/build-render-check.py
```

- **Inspection:**
  - Serve `render-check/index.html` locally (`python3 -m http.server -d render-check`) and verify diagram output.

## 6. Connect VS Code

- **Extension Configuration:**
  - Paste `<SERVICE_URL>` into `lightweightMarkdownViewer.d2.rendererUrl`.
  - Alternatively, select **Markdown: Choose D2 Renderer** in VS Code.

## Troubleshooting

| Symptom                                    | Cause                                                          | Fix                                                                |
| :----------------------------------------- | :------------------------------------------------------------- | :----------------------------------------------------------------- |
| `PERMISSION_DENIED` creating identity pool | Newly enabled APIs need up to a minute to accept IAM calls     | Wait 60 seconds, then re-run `scripts/gcp-setup.sh`                |
| Budget creation rejects call               | Budgets API requires an explicit quota project                 | Use the latest `scripts/gcp-setup.sh` (passes `--billing-project`) |
| Budget rejects currency amount             | Specified currency suffix does not match billing account       | Check `gcloud billing accounts describe` and use that currency     |
| Deploy job fails at authentication         | Branch is not `main`, repository differs, or variables missing | Verify `gh variable list` and confirm GitHub repo name matches     |
| Cloud Run cannot pull image                | GHCR package visibility is private                             | Set package visibility to public in GitHub Container Registry      |

Draw `d2` fences in VS Code with [Lightweight Markdown Preview](https://marketplace.visualstudio.com/items?itemName=KunalPathak.lightweight-markdown-preview).

## Navigation

- [Documentation index](./README.md)
- Previous: [Architecture](./030-architecture.md) · Next: [Operations](./050-operations.md)
