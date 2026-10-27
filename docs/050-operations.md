# Operations

Day-to-day care of the deployed service: health, cost, rollback, logs, tuning and teardown. Placeholders are explained in [040-deploy-gcp.md](./040-deploy-gcp.md#values-to-gather).

## Check the service

Three commands show whether the live service matches the latest build.

- **Revision and image:**
  - Confirm the ready revision runs the commit you expect.

```bash
gcloud run services describe d2-renderer --project=<PROJECT_ID> --region=<REGION> \
  --format='value(status.latestReadyRevisionName,spec.template.spec.containers[0].image)'
```

- **Behavior:**
  - The probe script sends about a dozen small read-only requests and prints a table. Run it against two targets and compare the output.

```bash
python3 scripts/probe-behavior.py <SERVICE_URL>
```

- **Pictures:**
  - The render check page shows every sample diagram from the local container and the deployed service. Steps are in [TESTING.md](../TESTING.md#visual-verification).

## Cost model

Cloud Run bills only while a request runs, rounded up to 100 ms, and scales to zero otherwise. Google's [pricing page](https://cloud.google.com/run/pricing) lists a monthly free allowance for request-based billing: 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests. Check the page for current numbers.

- **Free allowance by region:**
  - Google applies the allowance as a spending discount at **Tier 1** prices, shared across all projects on one billing account.
  - Tier 1 EU regions are Belgium, Netherlands, Finland, Stockholm, Madrid, Milan and Paris.
  - Frankfurt, London, Zurich and Berlin are Tier 2 and use the allowance up faster.
- **Outbound data:**
  - Google bills outbound data. The free 1 GiB covers North America only, so EU traffic costs a little.
  - SVGs are small, and browsers cache them for a year.
- **What `max-instances=1` limits:**
  - It limits how fast cost can grow.
  - It does not limit the monthly total. One busy instance all month would exceed the free allowance.
- **Budget alert:**
  - The alert sends email. It does **not** stop spending.
  - Google's [automatic billing shutoff](https://docs.cloud.google.com/billing/docs/how-to/disable-billing-with-notifications) disables billing for the whole project, may lag, and can delete resources.
  - This project does not use the shutoff ([decision 050](./decisions/050-traffic-limits-and-cost-guardrails.md)).
- **Monthly review:**
  - After the first month, read the billing report and decide whether the limits need adjusting.
  - A report near zero and no alert emails mean the defaults fit.

## Images and tags

The publish job pushes each build under three tags, and every tag points to a multi-architecture manifest.

| Tag              | Use it for                                                                                 |
| :--------------- | :----------------------------------------------------------------------------------------- |
| `latest`         | Local runs that should follow the newest build.                                            |
| Short commit SHA | Pinning a local run to one build.                                                          |
| Full commit SHA  | Deploys. Cloud Run never serves a cached older image, because each deploy names a new tag. |

## Rollback

A bad deploy is undone in seconds, without a rebuild. List revisions, then send all traffic to a known-good one:

```bash
gcloud run revisions list --service=d2-renderer --project=<PROJECT_ID> --region=<REGION>
gcloud run services update-traffic d2-renderer --project=<PROJECT_ID> --region=<REGION> --to-revisions=<REVISION_NAME>=100
```

The next push to `main` deploys forward again.

## Logs

```bash
gcloud run services logs read d2-renderer --project=<PROJECT_ID> --region=<REGION> --limit=50
```

Request lines include the diagram URL, which can contain diagram text. Keep personal data out of diagrams.

## Tuning limits

The service reads these environment variables. Set one on the running service without a rebuild:

| Variable                 | Default | Raise it when                                                                                |
| :----------------------- | :------ | :------------------------------------------------------------------------------------------- |
| `RENDER_TIMEOUT_SECONDS` | 20      | Large diagrams legitimately need longer. Keep it below the Cloud Run request timeout (30 s). |
| `MAX_SOURCE_BYTES`       | 262144  | Real diagrams exceed 256 KiB.                                                                |

```bash
gcloud run services update d2-renderer --project=<PROJECT_ID> --region=<REGION> --update-env-vars=RENDER_TIMEOUT_SECONDS=<SECONDS>
```

Concurrency, memory and instance limits live in the deploy job of [ci.yml](../.github/workflows/ci.yml). Change them there so the next deploy keeps them.

## Teardown

Deleting the project removes the service, identities and trust setup in one step, and stops all billing from it.

```bash
gcloud projects delete <PROJECT_ID>
```

Then delete the `GCP_*` repository variables, and the budget if it remains in the billing account. The deploy job skips itself once `GCP_PROJECT_ID` is gone.

## Navigation

- [Documentation index](./README.md)
- Previous: [Deploy runbook](./040-deploy-gcp.md)
