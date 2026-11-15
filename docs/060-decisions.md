# Architectural Decision Records

Each record is an active rule: the approach in force, what was rejected, and when to reopen it. Edit a record in place when the rule changes. When a requirement replaces a record, set `Status: Superseded by Decision XXX` and keep it. History and dates live in git.

The "Revisit decision when" conditions are inferred from each record's stated consequences.

| Decision                                                                         | Governs                                     |
| :------------------------------------------------------------------------------- | :------------------------------------------ |
| [001](#decision-001---belgium-europe-west1-as-the-cloud-run-region)              | Cloud Run region                            |
| [002](#decision-002---open-service-with-no-shared-secret)                        | Public access and authentication            |
| [003](#decision-003---keyless-workload-identity-federation-for-deploys)          | Deploy credentials                          |
| [004](#decision-004---cloud-run-pulls-the-public-ghcr-image-directly)            | Image delivery to Cloud Run                 |
| [005](#decision-005---traffic-limits-and-a-budget-alert-not-a-hard-cap)          | Cost and abuse guardrails                   |
| [006](#decision-006---offline-compile-in-an-empty-directory)                     | D2 compiler isolation                       |
| [007](#decision-007---committed-svg-files-for-documentation-diagrams)            | Diagrams in docs                            |
| [008](#decision-008---multi-architecture-image-linuxamd64-and-linuxarm64)        | Published image platforms                   |
| [009](#decision-009---on-demand-cloud-run-deployment-with-iam-perimeter-control) | Deploy trigger and public access toggle     |
| [010](#decision-010---local-daemon-management-script)                            | Running the native server in the background |

## Decision 001 - Belgium (`europe-west1`) as the Cloud Run region

Status: Accepted

### Decision context

The service processes requests in the EU. Cloud Run's free allowance is calculated at Tier 1 prices, so a Tier 2 region (Frankfurt, London, Zurich, Berlin) uses it up faster.

### Selected approach

- Deploy to `europe-west1` (Belgium), a Tier 1 EU region.
- Keep the region a parameter in the setup script and workflow variables, so forks can choose another.
- Processing and request logs stay in the EU. This is data location, not full GDPR compliance, because request logs contain diagram URLs.
- The container image is pulled from GitHub, which is outside the EU. The image holds code, not user data.
- Free-tier outbound data (1 GiB) covers North America only, so EU egress is billed. Volume is small.
- Latency is higher for users far from Belgium.

### Rejected approaches

- `Iowa (us-central1)`: the usual free-tier example, but not in the EU.
- `Frankfurt`: closer to many EU users, but Tier 2 pricing.

### Revisit decision when

- Egress or latency becomes a measurable problem for real users.
- Google changes which regions count as Tier 1.

## Decision 002 - Open service with no shared secret

Status: Accepted

### Decision context

The intended use is `<img src>` tags on public pages, which cannot send headers. An optional token (header or `?token=`) was proposed to reject bots cheaply.

### Selected approach

- Use no authentication. The service protects itself with the size and time limits in [Decision 005](#decision-005---traffic-limits-and-a-budget-alert-not-a-hard-cap).
- Anyone can render diagrams, up to those limits and one instance.
- Abuse shows up as cost or cache churn. The budget alert is the signal.

### Rejected approaches

- `Token in the URL`: visible to anyone who views the page source, so it stops only crawlers that never read the page. It also lands in request logs.
- `Cloud Run IAM (private service)`: browsers cannot authenticate image requests, and a signing proxy adds moving parts for a personal service.
- `Cloud Armor or a load balancer`: real protection, but not free.

### Revisit decision when

- Abuse appears in cost, cache churn or the budget alert. Then consider allowlisting origins at an edge proxy.

## Decision 003 - Keyless workload identity federation for deploys

Status: Accepted

### Decision context

GitHub Actions deploys to Cloud Run. The repository and workflow are public, so any stored credential is a leak risk.

### Selected approach

- Use workload identity federation. GitHub signs a short-lived token for each run, and Google accepts it only when it claims `<owner>/<repo>` on `refs/heads/main`.
- Set that condition on the identity provider, because IAM bindings cannot test token claims such as the branch.
- Give the deployer account `run.admin` on the project and `serviceAccountUser` on the runtime account only.
- Run the container as a separate account with no roles.
- Forks and pull requests cannot deploy, because their tokens fail the condition. A fork owner repeats the setup with their own repository name ([runbook](./010-setup/030-cloud-run.md)).
- A leaked workflow file reveals identifiers but grants nothing.

### Rejected approaches

- `Service account JSON key stored as a GitHub secret`: long-lived, leaks silently, needs rotation.
- `serviceAccountUser on the whole project`: wider than needed.

### Revisit decision when

- Deploys must run from a branch other than `main` or from a different repository.

## Decision 004 - Cloud Run pulls the public GHCR image directly

Status: Accepted

### Decision context

CI already publishes the image to GitHub Container Registry. Mirroring it into Artifact Registry adds a repository, storage cost and setup steps.

### Selected approach

- Keep the GHCR package public and deploy `ghcr.io/<owner>/<repo>:<full commit SHA>`.
- Use a unique tag per build, because Cloud Run caches images by tag.
- Keep registry credentials out of every system.
- Deploys depend on GHCR availability.

### Rejected approaches

- `Artifact Registry remote repository`: needed only for private images. Google also suggests it for availability.
- `Deploying with the latest tag`: Cloud Run may serve a cached older image for up to an hour.

### Revisit decision when

- The image must become private. A private package needs the remote repository route.
- GHCR availability causes failed deploys.

## Decision 005 - Traffic limits and a budget alert, not a hard cap

Status: Accepted

### Decision context

The service is public and each uncached render starts a process. Google Cloud has no built-in hard spending cap, and budgets only send email. The only automatic stop detaches billing from the project, which takes everything down, may lag, and can delete resources.

### Selected approach

- Cloud Run: one instance maximum, minimum zero, concurrency 8, request timeout 30 s, 1 vCPU and 512 MiB.
- Service: 20 s render limit, 256 KiB input limit and a 256-entry cache (see [architecture](./030-architecture.md)).
- Budget alert at 50% and 100% of a small amount.
- Worst-case cost is bounded in rate but not in monthly total. A sustained flood is noticed through the alert, not stopped.
- Normal personal use stays far inside the free allowance.
- Limits are env-tunable without a rebuild ([operations](./050-operations.md#tuning-limits)).

### Rejected approaches

- `Automatic billing shutoff`: too blunt for a hobby service, and not instantaneous.
- `Concurrency 40 and a 10 s timeout`: 40 parallel D2 processes risk running out of memory, and 10 s may clip large diagrams.
- `Always-on instance`: costs money while idle.

### Revisit decision when

- The alert fires, or the monthly bill exceeds the free allowance.
- Real diagrams hit the 20 s or 256 KiB limits.

## Decision 006 - Offline compile in an empty directory

Status: Accepted

### Decision context

D2 bundles `icon:` and image assets by downloading them while it compiles, and it resolves imports (`...@name`) against the working directory. On a public, open service ([Decision 002](#decision-002---open-service-with-no-shared-secret)), a diagram could make the container request any address it named. A measured probe against the deployed service reached the Cloud Run metadata server and received its `403` reply. Imports could read `.d2` files next to the server. The main local use is the VS Code extension, which draws every diagram through an `<img>` tag.

### Selected approach

- Run `d2` with `--bundle=false`. The compiler makes no network requests, and icon and image URLs stay in the SVG as `<image href>` references.
- Run each compile in a fresh empty temporary directory, so imports see nothing.
- Describe renders as self-contained, deterministic and private. Diagrams that need hosted icons use a renderer built for that, such as Kroki.
- No outbound request can be triggered by a diagram, on any host that runs the image.
- A diagram with an icon compiles in milliseconds instead of failing when an icon host is slow or returns an error.
- Browsers do not load external resources inside an SVG shown through `<img>`, so icon positions show the browser's placeholder. Diagrams without icons are unaffected.
- Tests: `TestOfflineCompile` in [test_server.py](../tests/test_server.py).

### Rejected approaches

- `ICON_HOSTS allowlist with address checks`: D2 performs the download itself, so Python cannot police DNS results or redirects from outside. It needs a pre-fetch layer or an egress proxy, and a setting to maintain.
- `Rewriting the SVG to delete image tags`: extra code that changes compiler output, with no safety gain over never fetching.
- `Egress firewall on Cloud Run`: protects one deployment only, and costs money and configuration.

### Revisit decision when

- Users need hosted icons rendered by this service.
- D2 gains a built-in way to restrict or proxy downloads.

## Decision 007 - Committed SVG files for documentation diagrams

Status: Accepted

### Decision context

The docs once showed diagrams as `<img>` tags that pointed at `http://localhost:8080`. GitHub cannot reach a localhost address, so readers saw broken images. GitHub also shows a `d2` code fence as plain code.

### Selected approach

- Draw each documentation diagram with this project's own container, using the bundled TALA layout engine, and commit the SVG next to the docs.
- Show the SVG with an `<img>` tag that sets a width, and give the D2 source in a collapsible block beneath it. D2's SVG declares only a `viewBox`, so browsers otherwise pick a small default size.
- Keep sources in `docs/070-diagrams/` and `docs/090-examples/`. `scripts/build-doc-diagrams.py` renders them, and `--check` fails CI when an SVG or an embedded source drifts.
- Regenerate an SVG in the same commit as its `.d2` change.
- Arm64 and amd64 builds produce byte-identical SVGs (checked for every diagram), so the CI check holds on any runner.
- Diagrams render on GitHub, in editors and offline.

### Rejected approaches

- `Raw inline <svg> in Markdown`: GitHub removes it.
- `PNG files`: need a headless browser in the build, lose crisp text at zoom, and weigh more. D2's SVG embeds its fonts, so it rendered correctly in every browser check run for this project.
- `Mermaid for every diagram`: GitHub draws it, but the project documents D2, and its own output is the best proof it works.
- `Rendering at view time from a hosted service`: puts a third party in the reading path and exposes diagram text.

### Revisit decision when

- GitHub renders `d2` code fences natively.
- Arm64 and amd64 renders stop matching byte for byte.

## Decision 008 - Multi-architecture image (`linux/amd64` and `linux/arm64`)

Status: Accepted

### Decision context

The main local use is a container on a developer machine, and many of those machines are Apple Silicon Macs. An amd64-only image failed to pull there with "no matching manifest for linux/arm64/v8". Cloud Run needs amd64.

### Selected approach

- Build one manifest list with both platforms, using QEMU and buildx in the publish job.
- Fail the publish job unless `docker buildx imagetools inspect` lists both platforms.
- Keep deploying the commit-SHA tag. Cloud Run selects the amd64 entry.
- One `docker run` command works on Intel, AMD and Arm hosts.
- The publish job runs longer because the arm64 build is emulated.
- Both platforms render the bundled TALA layout. The arm64 image was run natively on an Apple Silicon Mac.

### Rejected approaches

- `Other architectures (arm/v7, 386, riscv64, ppc64le, s390x)`: the `d2lang/d2` image publishes only amd64 and arm64, so each would need D2 built from source.
- `Separate tags per architecture`: users would have to choose, and the quickstart would need a flag.

### Revisit decision when

- The `d2lang/d2` image adds another architecture.
- The emulated arm64 build time becomes a burden. Native arm64 runners would remove it.

## Decision 009 - On-demand Cloud Run deployment with IAM perimeter control

Status: Accepted

### Decision context

The Cloud Run deployment is a technology demonstrator and on-demand personal utility, not an always-on public daemon. Diagram URLs are embedded in public pages or VS Code previews only during active testing or demonstrations.

Coupling deployments to everyday pushes caused two problems:

- Every push to `main` redeployed with `--allow-unauthenticated`, which reopened the service even when the maintainer kept it offline.
- Pausing deploys with a repository variable (`DEPLOY_ENABLED`) created split-brain state between GitHub and Google Cloud IAM, caused silent CI skips and complicated operations.

### Selected approach

- Pushes to `main` test the code and publish multi-architecture images to GHCR. They never touch live Cloud Run state.
- The `deploy` job runs only on manual dispatch (`workflow_dispatch`), for example `gh workflow run ci.yml`.
- Deploys pass `--no-allow-unauthenticated`, so a code update never exposes the service.
- Public access is a one-command IAM change at the Google edge:
  - Up: `gcloud run services add-iam-policy-binding d2-renderer ... --member=allUsers --role=roles/run.invoker`
  - Down: `gcloud run services remove-iam-policy-binding d2-renderer ... --member=allUsers --role=roles/run.invoker`
- The repository keeps no deploy-pause variables.
- When offline, requests return `403 Forbidden` at Google Frontend without reaching Cloud Run, so 0 instances run and nothing is billed.
- Forks and new maintainers can push freely without accidental cloud deployments.

### Rejected approaches

- `Auto-deploy on every push with --allow-unauthenticated`: forces the service online on every commit, overriding intentional shutdowns.
- `Auto-deploy on every push with --no-allow-unauthenticated`: strips public access on every commit, even when the maintainer opened it for a demonstration.
- `Pause deploys with repository variables`: creates split-brain state, silent CI skips and multi-step manual overhead.
- `max-instances=0`: the Knative and Cloud Run control planes require `maxScale >= 1`.

### Revisit decision when

- The service must stay permanently public with continuous deployment.
- The manual dispatch step becomes a recurring source of stale deployments.

## Decision 010 - Local daemon management script

Status: Accepted

### Decision context

`d2-renderer` runs natively as standard-library Python (`python3 server.py`) alongside Docker and Google Cloud Run. The native footprint suits developer machines: about 26 MB of resident memory and about 100 ms to first healthy response, measured on the maintainer's Mac, with no container runtime.

Running the native server in the background has four problems:

- `python3 server.py` holds the terminal unless the user backgrounds it with `nohup ... &`.
- Stopping a background process by hand (`lsof -ti :8088 | xargs kill`) can kill unrelated processes that use the port.
- Desktop automations (macOS Shortcuts, Raycast, Alfred, VS Code tasks, cron) run with a minimal `PATH` (`/usr/bin:/bin`) and do not find Python 3.12 or `d2` without extra setup.
- `launchd` and `systemd` need unit files with absolute paths, which makes ad-hoc start, stop and toggle awkward.

### Selected approach

Provide `scripts/manage-daemon.sh`, a bash script with no dependencies beyond bash, curl, ps, kill, nohup and Python 3.12:

- **Commands:** `up`, `down`, `toggle`, `status`, `restart` and `logs`. `up` and `down` are idempotent.
- **Shell:** bash, not POSIX `sh`. The script avoids bash 4 features so it runs on the macOS system bash 3.2.
- **PATH recovery:** it prepends `~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin` and the Linuxbrew bin directory before it looks for Python and `d2`.
- **State:** PID and log files live in `$D2_STATE_DIR` (default `~/.d2-renderer/`), named by port, so the git working tree stays clean and several daemons can coexist.
- **Ownership:** the PID file is the only proof that the script started a process. If another process answers on the port, `up`, `down` and `toggle` report an error and never kill it. `status` reports it as unmanaged.
- **Shutdown:** `SIGTERM`, then `SIGKILL` after 3 seconds. The server keeps no state that needs a clean shutdown.
- **Exit codes:** `status` returns 0 when the server answers and 1 when it does not.
- **Location:** `scripts/`, so `server.py` and the `Dockerfile` remain the canonical entry points.
- **Failure handling:** a start that fails reports the last log lines and leaves no PID file.
- **Log growth:** the log file never rotates. Users delete it when it grows too large.
- **Tests:** `tests/test_manage_daemon.py` starts its own servers on free ports and runs in every CI job that runs `unittest discover`.

### Rejected approaches

- `run.sh at the repository root`: it ranks a convenience helper with the primary entry points and confuses container-first users.
- `Wrapping Docker commands`: `docker run -d` and `docker stop` already provide this.
- `Python daemonizer packages (daemonocle, supervisor)`: they break the rule of no dependencies beyond the standard library.
- `launchd or systemd alone`: they leave ad-hoc starts and one-command toggles unsupported. The `launchd` recipe stays in the [local Python guide](./010-setup/020-local-python.md) for persistent use.
- `Finding the process by port with lsof`: it can match clients and unrelated services, and `lsof` is not on a bare `PATH`.

### Revisit decision when

- The log file growth causes real problems.
- Windows support becomes a requirement.
