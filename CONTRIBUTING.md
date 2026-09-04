# Contributing to Bessemer

Thank you for your interest in contributing to Bessemer! This guide walks you through setting up the repository, initializing the backend development environment, and submitting your contributions.

---

## Repository Information

- **Git Repository**: [https://github.com/kbpramod/bessemer.git](https://github.com/kbpramod/bessemer.git)
- **Default Branch**: `main`

---

## Prerequisites & Version Requirements

Before initializing the backend, ensure you have the following installed on your system:

| Tool | Required Version | Notes |
| :--- | :--- | :--- |
| **Git** | `2.x+` | Version control system |
| **Python** | `>= 3.11` | Defined in `.python-version` and `pyproject.toml` |
| **uv** | `>= 0.12.0` | Fast Python package and project manager (recommended) |

> **Note:** If you don't have Python 3.11 installed on your system, `uv` can download and manage it for you automatically.

---

## Getting Started

### 1. Clone the Repository

Clone the project from GitHub and navigate into the workspace:

```bash
git clone https://github.com/kbpramod/bessemer.git
cd bessemer
```

---

## Backend Initialization

The backend is built with Python, FastAPI, and managed with [uv](https://docs.astral.sh/uv/).

### 1. Navigate to the Backend Directory

```bash
cd backend
```

### 2. Install `uv` (if not already installed)

If you haven't installed `uv` yet, install it using the official installer:

- **macOS / Linux**:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Windows (PowerShell)**:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **Via Pip** (alternative):
  ```bash
  pip install uv
  ```

Verify installation:
```bash
uv --version
```

### 3. Install Python 3.11 (via `uv`)

If you don't have Python 3.11 installed locally, `uv` can install it directly:

```bash
uv python install 3.11
```

### 4. Create Virtual Environment & Sync Dependencies

Run `uv sync` from inside the `backend` directory. This will automatically read `pyproject.toml` and `uv.lock`, create a `.venv` virtual environment, and install all required dependencies (FastAPI, Uvicorn, etc.):

```bash
uv sync
```

### 5. Activate the Virtual Environment (Optional)

You can activate the virtual environment if you want to run commands directly:

- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **macOS / Linux**:
  ```bash
  source .venv/bin/activate
  ```

> **Tip:** With `uv`, activating the virtual environment is optional. You can prefix any command with `uv run` to automatically execute it within the environment.

---

## Running the Backend

### Run Entrypoint Script

To execute the backend application entrypoint:

```bash
uv run backend
```

Expected output:
```text
Hello from backend!
```

### Run FastAPI Development Server

When running the FastAPI server with auto-reload enabled:

```bash
uv run uvicorn backend:app --reload --host 127.0.0.1 --port 8000
```
*(Adjust the module/app path as the FastAPI application routes are developed.)*

---

## Backend Dependencies

Current key dependencies defined in `pyproject.toml`:

- **Python**: `>= 3.11`
- **FastAPI**: `>= 0.141.1`
- **Uvicorn**: `>= 0.52.4` (standard extras)
- **Build backend**: `uv_build` (`>=0.12.0, <0.13.0`)

To add new dependencies:
```bash
uv add <package-name>
```

To add development-only dependencies:
```bash
uv add --dev <package-name>
```

---

## Contribution Workflow

We follow a standard Git feature branch workflow:

### 1. Create a New Branch

Keep `main` clean and create a descriptive branch for your changes:

```bash
git checkout -b feat/your-feature-name
```
*Naming convention: `feat/...`, `fix/...`, `docs/...`, `refactor/...`*

### 2. Make Your Changes

- Follow consistent Python formatting and style guidelines.
- Keep dependencies updated in `pyproject.toml` and lockfile (`uv.lock`).

### 3. Commit Your Changes

Write meaningful commit messages:

```bash
git add .
git commit -m "feat(backend): implement initialization workflow"
```

### 4. Push to GitHub

```bash
git push -u origin feat/your-feature-name
```

### 5. Open a Pull Request

1. Go to the repository at [https://github.com/kbpramod/bessemer](https://github.com/kbpramod/bessemer).
2. Click **Compare & pull request**.
3. Fill out the PR description with a summary of your changes and reference any related issues.
4. Request reviews from maintainers.
