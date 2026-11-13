# D2 Render Verification Document

This document contains **unrendered D2 diagram specifications**. Use this file to verify that your `d2-renderer` instance is running and properly integrated with your authoring environment.

## How to Test

### Method 1: In VS Code (Interactive Live Preview)
1. Install [Lightweight Markdown Preview](https://marketplace.visualstudio.com/items?itemName=KunalPathak.lightweight-markdown-preview).
2. Start `d2-renderer` locally (via Docker or native Python) or in the cloud.
3. Open VS Code Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`) and run **Markdown: Choose D2 Renderer**.
4. Point it to your renderer URL (e.g. `http://localhost:8080`).
5. Open the Markdown Preview (`Cmd+Shift+V` / `Ctrl+Shift+V`). Every code fence below should render as an interactive SVG diagram.

### Method 2: Via Terminal (`curl`)
Copy any snippet below and stream it to your running renderer:

```bash
printf 'client -> server: request\nserver -> client: response' | curl -X POST --data-binary @- http://localhost:8080/d2/svg -o test.svg
```

---

## Test Cases

### 1. Basic Flow (Directional Graph)

```d2
direction: right

Client: Developer Browser
Service: d2-renderer microservice

Client -> Service: POST /d2/svg (raw D2 text)
Service -> Client: 200 OK (SVG image)
```

### 2. Nested Containers & Infrastructure Topology

```d2
direction: right

Cloud: Cloud Environment {
  style.fill: "#F4F6F8"

  VPC: Virtual Private Cloud {
    style.fill: "#E8F0FE"

    PublicSubnet: Public Subnet {
      Gateway: API Gateway {
        shape: hexagon
      }
    }

    PrivateSubnet: Private Subnet {
      App: Application Service {
        shape: rectangle
      }
      Cache: Redis Cache {
        shape: cylinder
      }
      DB: PostgreSQL Database {
        shape: cylinder
      }
    }
  }
}

Gateway -> App: Proxy request
App -> Cache: Query session
App -> DB: Query records
```

### 3. Sequence Diagram (Authentication Flow)

```d2
shape: sequence_diagram

User: User Browser
App: Web Application
Auth: Identity Provider

User -> App: 1. Request protected page
App -> User: 2. Redirect to login
User -> Auth: 3. Submit credentials
Auth -> User: 4. Issue auth token
User -> App: 5. Present token
App -> User: 6. Serve requested page
```

### 4. Database Schema (`sql_table`)

```d2
users: Users {
  shape: sql_table
  id: int {constraint: primary_key}
  email: varchar(255) {constraint: unique}
  created_at: timestamp
}

projects: Projects {
  shape: sql_table
  id: int {constraint: primary_key}
  user_id: int {constraint: foreign_key}
  name: varchar(100)
}

users.id -> projects.user_id: One-to-Many
```

### 5. Hand-Drawn Sketch Aesthetic

```d2
vars: {
  d2-config: {
    sketch: true
  }
}

Idea -> Experiment: Quick test
Experiment -> Production: High confidence
Experiment -> Backlog: Needs iteration
```

---

## Result Verification

- If all diagrams render as clean SVGs, your renderer and client setup are fully operational.
- If diagrams show as raw code fences, verify that your renderer URL is configured and `curl http://localhost:8080/health` returns `OK`.
