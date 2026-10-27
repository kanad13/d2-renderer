#!/usr/bin/env bash
# One-time Google Cloud setup for deploying d2-renderer from GitHub Actions.
#
# Why a script: the steps must be repeatable by anyone who forks this repo, so every
# account-specific value comes from an environment variable, never from this file.
# Run it as an account that can create projects and link billing. See docs/040-deploy-gcp.md.
#
# Required:
#   PROJECT_ID          new or existing project id (globally unique)
#   BILLING_ACCOUNT_ID  open billing account to link (gcloud billing accounts list)
#   GITHUB_REPO         <owner>/<repo> allowed to deploy, e.g. your-user/d2-renderer
# Optional:
#   REGION              Cloud Run region (default europe-west1, a free-tier-eligible EU region)
#   BUDGET_AMOUNT       alert threshold in the billing account's currency, e.g. 5USD (default 5)
#                       The suffix must match the account currency.

set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${BILLING_ACCOUNT_ID:?set BILLING_ACCOUNT_ID}"
: "${GITHUB_REPO:?set GITHUB_REPO as <owner>/<repo>}"
REGION="${REGION:-europe-west1}"
BUDGET_AMOUNT="${BUDGET_AMOUNT:-5USD}"

POOL_ID="github-pool"
PROVIDER_ID="github-provider"
DEPLOYER_SA="github-deployer"
RUNTIME_SA="d2-renderer-runtime"

step() { printf '\n==> %s\n' "$1"; }

step "Create project (skipped if it exists)"
if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud projects create "$PROJECT_ID" --name="d2-renderer"
fi

step "Link billing account"
# Cloud Run cannot deploy without billing, even when usage stays inside the free tier.
gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT_ID"

step "Enable APIs"
# sts + iamcredentials let GitHub's token be exchanged for a short-lived Google identity.
gcloud services enable --project="$PROJECT_ID" \
  run.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  cloudresourcemanager.googleapis.com \
  billingbudgets.googleapis.com

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
DEPLOYER_EMAIL="${DEPLOYER_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
RUNTIME_EMAIL="${RUNTIME_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

step "Create service accounts"
# Deployer: used only by GitHub Actions. Runtime: the identity the container runs as,
# kept with zero roles so a compromised container can reach nothing in the project.
gcloud iam service-accounts describe "$DEPLOYER_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1 ||
  gcloud iam service-accounts create "$DEPLOYER_SA" --project="$PROJECT_ID" --display-name="GitHub deployer"
gcloud iam service-accounts describe "$RUNTIME_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1 ||
  gcloud iam service-accounts create "$RUNTIME_SA" --project="$PROJECT_ID" --display-name="d2-renderer runtime"

step "Grant deployer permissions"
# run.admin is needed to deploy and to make the service publicly invokable.
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_EMAIL}" --role="roles/run.admin" --condition=None >/dev/null
# Scoped to the runtime account only, not the whole project.
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_EMAIL" --project="$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_EMAIL}" --role="roles/iam.serviceAccountUser" >/dev/null

step "Create workload identity pool and GitHub provider"
gcloud iam workload-identity-pools describe "$POOL_ID" --project="$PROJECT_ID" --location=global >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools create "$POOL_ID" --project="$PROJECT_ID" --location=global \
    --display-name="GitHub Actions"
# The attribute condition is the real gate: tokens from any other repository, or from
# any branch other than main, are rejected before they can touch the service account.
gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" --project="$PROJECT_ID" \
  --location=global --workload-identity-pool="$POOL_ID" >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" --project="$PROJECT_ID" \
    --location=global --workload-identity-pool="$POOL_ID" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref,attribute.actor=assertion.actor" \
    --attribute-condition="assertion.repository=='${GITHUB_REPO}' && assertion.ref=='refs/heads/main'"

step "Allow the pool to impersonate the deployer"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_EMAIL" --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${GITHUB_REPO}" >/dev/null

step "Create budget alert"
# A budget only emails billing admins; it does not stop spending. It is the early warning.
# --billing-project is required: the budgets API rejects calls that have no quota project.
BUDGET_NAME="d2-renderer ${PROJECT_ID}"
if ! gcloud billing budgets list --billing-account="$BILLING_ACCOUNT_ID" --billing-project="$PROJECT_ID" \
  --format='value(displayName)' | grep -qxF "$BUDGET_NAME"; then
  gcloud billing budgets create --billing-account="$BILLING_ACCOUNT_ID" --billing-project="$PROJECT_ID" \
    --display-name="$BUDGET_NAME" \
    --filter-projects="projects/${PROJECT_NUMBER}" \
    --budget-amount="$BUDGET_AMOUNT" \
    --threshold-rule=percent=0.5 \
    --threshold-rule=percent=1.0 >/dev/null
fi

step "Done. Save these as GitHub repository variables (Settings > Secrets and variables > Actions > Variables)"
cat <<EOF
GCP_PROJECT_ID=${PROJECT_ID}
GCP_REGION=${REGION}
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}
GCP_DEPLOYER_SERVICE_ACCOUNT=${DEPLOYER_EMAIL}
GCP_RUNTIME_SERVICE_ACCOUNT=${RUNTIME_EMAIL}
EOF
