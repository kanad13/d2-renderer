# Deploy to Google Cloud Run

Runbook for setting up and deploying an on-demand, serverless instance of `d2-renderer` to Google Cloud Run.

- **Audience & Scope:**
  - Designed for maintainers or teams establishing a shared, always-available cloud renderer.
  - Used for embedding live diagram URLs in public GitHub READMEs, wikis, or internal portals without running local processes.
- **Deployment Model:**
  - GitHub Actions runs tests and publishes container images to GHCR on pushes to `main`.
  - Cloud Run deployments run on demand via manual workflow dispatch (`gh workflow run ci.yml`).
  - Deployments configure `--no-allow-unauthenticated` by default to prevent accidental public exposure.
  - Public access is controlled on demand using the 1-command IAM toggle in [Operations](../050-operations.md#control-public-access-up-and-down).

## Values to Gather

| Placeholder | Meaning | How to Find It |
| :--- | :--- | :--- |
| `<PROJECT_ID>` | New Google Cloud project ID, globally unique (e.g. `d2-renderer-<random>`) | You choose it |
| `<BILLING_ACCOUNT_ID>` | An **open** Google Cloud billing account | `gcloud billing accounts list` |
| `<GITHUB_REPO>` | `<owner>/<repo>` authorized to deploy | Your repository address on GitHub |
| `<REGION>` | Cloud Run region (Tier 1 EU region recommended, e.g. `europe-west1`) | Your data-location needs |
| `<BUDGET_AMOUNT>` | Alert threshold in billing account currency (e.g. `5USD`) | `gcloud billing accounts describe <BILLING_ACCOUNT_ID>` |

## Prerequisites

- A Google Cloud account with project creation permissions.
- The [`gcloud` CLI](https://cloud.google.com/sdk/docs/install) authenticated locally.
- The [`gh` CLI](https://cli.github.com) authenticated with admin rights to `<GITHUB_REPO>`.
- A public GitHub Container Registry package so Cloud Run can pull images without credentials ([decision 040](../060-decisions/040-public-image-pulled-directly.md)).

## 1. Sign in

```bash
gcloud auth login
```

## 2. Automated Provisioning

The provisioning script links billing, enables required APIs, sets up keyless Workload Identity Federation, and creates deployer and runtime service accounts:

```bash
PROJECT_ID=<PROJECT_ID> \
BILLING_ACCOUNT_ID=<BILLING_ACCOUNT_ID> \
GITHUB_REPO=<GITHUB_REPO> \
REGION=<REGION> \
BUDGET_AMOUNT=<BUDGET_AMOUNT> \
./scripts/gcp-setup.sh
```

The script prints five `NAME=value` lines required for GitHub Actions repository variables.

## 3. Save GitHub Repository Variables

Set non-secret repository variables so GitHub Actions can authenticate keylessly:

```bash
gh variable set GCP_PROJECT_ID -R <GITHUB_REPO> -b "<value printed by script>"
gh variable set GCP_REGION -R <GITHUB_REPO> -b "<value printed by script>"
gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER -R <GITHUB_REPO> -b "<value printed by script>"
gh variable set GCP_DEPLOYER_SERVICE_ACCOUNT -R <GITHUB_REPO> -b "<value printed by script>"
gh variable set GCP_RUNTIME_SERVICE_ACCOUNT -R <GITHUB_REPO> -b "<value printed by script>"
```

## 4. Trigger Deployment

Trigger the GitHub Actions deploy job explicitly ([decision 090](../060-decisions/090-on-demand-cloud-run-deployment.md)):

```bash
gh workflow run ci.yml -R <GITHUB_REPO>
```

Everyday pushes to `main` test and publish images but do not deploy automatically. The deploy job runs only when manually dispatched.

## 5. Retrieve URL & Verify

Retrieve the deployed Cloud Run service URL:

```bash
gcloud run services describe d2-renderer --project=<PROJECT_ID> --region=<REGION> --format='value(status.url)'
```

Generate the comparison check page to ensure diagrams render identically to local output:

```bash
RENDERER_REMOTE_URL=<SERVICE_URL> python3 scripts/build-render-check.py
```

Serve `render-check/index.html` locally and inspect diagram output.

## 6. Configure Clients

- **VS Code:** Set `lightweightMarkdownViewer.d2.rendererUrl` to `<SERVICE_URL>`, or select **Markdown: Choose D2 Renderer** in VS Code.
- **Public `<img>` tags:** See [Operations: Control Public Access](../050-operations.md#control-public-access-up-and-down) to toggle public access with one IAM command.

## Troubleshooting

| Symptom | Cause | Resolution |
| :--- | :--- | :--- |
| `PERMISSION_DENIED` creating identity pool | APIs need up to a minute to propagate | Wait 60 seconds and re-run `scripts/gcp-setup.sh`. |
| Deploy job fails at authentication | Branch is not `main` or repository variables mismatch | Verify `gh variable list` and confirm GitHub repo name matches. |
| Cloud Run cannot pull image | GHCR package visibility is set to private | Set package visibility to public in GitHub Container Registry. |

## Navigation

- [Setup Guide Index](./README.md)
- [Docker Setup](./010-docker.md)
- [Native Python Setup](./020-local-python.md)
- [Operations Guide](../050-operations.md)
