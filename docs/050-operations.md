# Operations

Operational runbook for managing service health, lifecycle state, deployments, cost guardrails, and teardown.

- **Operating Philosophy:**
  - The deployed service serves as an on-demand demonstrator and personal utility.
  - The container stays scaled to zero instances when idle, incurring zero computing cost.
  - Public invocation is toggled on demand via Google Cloud IAM policies.
  - Code changes pushed to `main` publish container images without modifying live Cloud Run state.

## Next time you want to use the service

Follow these direct steps whenever you need to run or test the service.

- **Option A: Run Locally (Recommended for Daily Editing):**
  - Keeps diagram text completely on your machine with zero network latency.
  - Start the container locally: `docker run -d --name d2-test -p 8080:8080 ghcr.io/kanad13/d2-renderer:latest`
  - Set `lightweightMarkdownViewer.d2.rendererUrl` in VS Code to `http://localhost:8080`.

- **Option B: Use the Cloud Run Deployment:**
  - Bring the service online before sharing previews or testing remote rendering:
    ```bash
    gcloud run services add-iam-policy-binding d2-renderer \
      --project=<PROJECT_ID> --region=<REGION> \
      --member=allUsers --role=roles/run.invoker
    ```
  - Retrieve the service URL:
    ```bash
    gcloud run services describe d2-renderer \
      --project=<PROJECT_ID> --region=<REGION> \
      --format='value(status.url)'
    ```
  - Set the URL in VS Code or embed it in documentation.
  - Take the service offline immediately when finished:
    ```bash
    gcloud run services remove-iam-policy-binding d2-renderer \
      --project=<PROJECT_ID> --region=<REGION> \
      --member=allUsers --role=roles/run.invoker
    ```

## Control public access (UP and DOWN)

Cloud Run scales to zero instances when idle. Controlling whether the public internet can wake the container is handled directly through its IAM invoker policy ([decision 090](./decisions/090-on-demand-cloud-run-deployment.md)).

- **Bring it online (allow public requests):**
  - Grants `allUsers` the invoker role, allowing incoming HTTP requests to wake the container on demand.

```bash
gcloud run services add-iam-policy-binding d2-renderer --project=<PROJECT_ID> --region=<REGION> --member=allUsers --role=roles/run.invoker
```

- **Take it offline (keep container dormant at 0 instances):**
  - Removes `allUsers`. Requests return `403 Forbidden` at Google Frontend without reaching Cloud Run, keeping instance count at 0.

```bash
gcloud run services remove-iam-policy-binding d2-renderer --project=<PROJECT_ID> --region=<REGION> --member=allUsers --role=roles/run.invoker
```

- **Call it privately while offline:**
  - Project members with invoker permissions can reach the service using an identity token even while public access is disabled.

```bash
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" <SERVICE_URL>/health
```

- **Proxy locally with authentication:**
  - Forwards authenticated requests through a local port without opening the service to the internet.

```bash
gcloud run services proxy d2-renderer --project=<PROJECT_ID> --region=<REGION> --port=8080
```

## Deploy updates to Cloud Run

Deployments are decoupled from regular git pushes to prevent accidental changes to runtime hosting state.

- **Continuous Integration on `main`:**
  - Pushing to `main` runs tests and publishes multi-architecture images (`linux/amd64`, `linux/arm64`) to GHCR.
  - The live Cloud Run revision is unchanged by git pushes.

- **Deploying a New Revision:**
  - Trigger the deployment workflow manually when you explicitly want to update Cloud Run:

```bash
gh workflow run ci.yml -R <GITHUB_REPO>
```

- **Deployment Safety Flag:**
  - The workflow passes `--no-allow-unauthenticated` so new deployments never expose the service unexpectedly.

## Check service status

Three commands verify that the live service matches your expectations.

- **Active Revision and Image:**
  - Confirm the ready revision runs the expected commit SHA.

```bash
gcloud run services describe d2-renderer --project=<PROJECT_ID> --region=<REGION> \
  --format='value(status.latestReadyRevisionName,spec.template.spec.containers[0].image)'
```

- **Behavior Probe:**
  - Run the automated probe script against the target to verify HTTP responses across endpoints.

```bash
python3 scripts/probe-behavior.py <SERVICE_URL>
```

- **Visual Render Check:**
  - Build the visual check page to compare local and remote rendering output.

```bash
RENDERER_REMOTE_URL=<SERVICE_URL> python3 scripts/build-render-check.py
```

## Cost model and guardrails

Cloud Run bills only while an instance processes requests (rounded up to 100 ms) and scales to zero otherwise.

- **Free Allowance by Region:**
  - Request-based billing includes monthly Tier 1 allowances: 180,000 vCPU-seconds, 360,000 GiB-seconds, and 2 million requests.
  - Tier 1 EU regions include Belgium (`europe-west1`), Netherlands, Finland, Madrid, Milan, and Paris.
  - Deployments must stay in a Tier 1 region ([decision 010](./decisions/010-eu-region-belgium.md)).
- **Instance Limit:**
  - Cloud Run enforces `max-instances=1` ([decision 050](./decisions/050-traffic-limits-and-cost-guardrails.md)).
  - Caps concurrent spending rate while allowing requests to queue.
- **Budget Alert:**
  - Triggers email notifications when projected monthly spend crosses the threshold.
  - Alerts notify maintainers but do not forcefully disable project billing, avoiding resource deletion.

## Images and tags

The publish job pushes each build under three tags, each referencing a multi-architecture manifest list.

| Tag              | Use Case                                                                   |
| :--------------- | :------------------------------------------------------------------------- |
| `latest`         | Local development following the newest build.                              |
| Short commit SHA | Pinning a local run to a specific known build.                             |
| Full commit SHA  | Cloud Run deploys. Guarantees Cloud Run never serves a cached older image. |

## Rollback

Roll back a problematic deployment in seconds without rebuilding images.

- **List Revisions:**
  - Retrieve the names of previously deployed revisions.

```bash
gcloud run revisions list --service=d2-renderer --project=<PROJECT_ID> --region=<REGION>
```

- **Shift Traffic:**
  - Route 100% of traffic immediately to a known-good revision.

```bash
gcloud run services update-traffic d2-renderer --project=<PROJECT_ID> --region=<REGION> --to-revisions=<REVISION_NAME>=100
```

## Logs

- **Inspect Recent Request Logs:**
  - Read recent request lines and diagnostic messages from Cloud Logging.

```bash
gcloud run services logs read d2-renderer --project=<PROJECT_ID> --region=<REGION> --limit=50
```

- **Privacy Caution:**
  - Request lines include the diagram URL path, which contains deflated diagram source text.
  - Keep sensitive or private credentials out of diagrams rendered on shared services.

## Tuning limits

Adjust execution limits on the live service without rebuilding container images.

| Variable                 | Default | Raise it when                                                               |
| :----------------------- | :------ | :-------------------------------------------------------------------------- |
| `RENDER_TIMEOUT_SECONDS` | 20      | Complex diagrams exceed compile limits. Keep below Cloud Run timeout (30s). |
| `MAX_SOURCE_BYTES`       | 262144  | Diagram specifications exceed 256 KiB.                                      |

```bash
gcloud run services update d2-renderer --project=<PROJECT_ID> --region=<REGION> --update-env-vars=RENDER_TIMEOUT_SECONDS=<SECONDS>
```

## Teardown

Remove all cloud resources and stop all billing in one step.

- **Delete Project:**
  - Deletes the Cloud Run service, service accounts, and workload identity pool.

```bash
gcloud projects delete <PROJECT_ID>
```

- **Clean Up GitHub:**
  - Delete `GCP_*` repository variables via `gh variable delete <NAME>`.

## Navigation

- [Documentation index](./README.md)
- Previous: [Deploy runbook](./040-deploy-gcp.md)
