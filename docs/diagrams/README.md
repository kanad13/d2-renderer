# Documentation diagrams

## Purpose

The D2 sources for the pictures in the project docs. Each `.d2` file here becomes `docs/img/<name>.svg`.

## Contents

| Source                                     | Used in                                | Shows                                                |
| :----------------------------------------- | :------------------------------------- | :--------------------------------------------------- |
| [local-use.d2](./local-use.d2)             | [README](../../README.md)              | VS Code sending a `d2` fence to the local container. |
| [request-flow.d2](./request-flow.d2)       | [Architecture](../030-architecture.md) | Size check, cache, compile and error paths.          |
| [offline-compile.d2](./offline-compile.d2) | [Architecture](../030-architecture.md) | An empty directory and `--bundle=false` per compile. |
| [deployment.d2](./deployment.d2)           | [Architecture](../030-architecture.md) | A push to `main` reaching Cloud Run.                 |

## Rebuild

Start the container, then run the build script from the repository root:

```bash
python3 scripts/build-doc-diagrams.py
```

`--check` reports stale images or embedded sources and runs in CI. Rationale: [decision 070](../decisions/070-static-svg-diagrams-in-docs.md).

## Navigation

- [Documentation index](../README.md)
