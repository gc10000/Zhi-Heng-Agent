# Product Knowledge RAG Migration Implementation Plan

> **For agentic workers:** Execute inline in the requested destination. No separate branch, publication, or algorithm optimization is requested.

**Goal:** Migrate the supplied course application to Product-Knowledge-Rag, identify missing runtime configuration, and establish a reproducible local startup path.

**Architecture:** Preserve the separate import (8000) and query (8001) FastAPI applications and their LangGraph workflows. Supply local configuration, infrastructure definitions and operational checks around the existing application.

**Tech Stack:** Python 3.12, FastAPI, LangGraph, Milvus, MinIO, MongoDB, BGE-M3, BGE reranker, DashScope, MinerU.

**Spec:** User request dated 2026-10-21: migrate involved code, inspect missing configuration for the user to fill in, get it running before optimization.

## Global Constraints

- Keep original project files untouched.
- Do not migrate original credentials, logs, generated outputs or course materials into public source files.
- Preserve provenance and any upstream license; do not invent a license or claim original authorship.
- Preserve the retrieval and ingestion algorithms; change only demonstrated setup/startup blockers.
- Distinguish HTTP startup, infrastructure readiness, and a real document-to-answer test.

### Task 1: Source and configuration audit

- [x] Read both API entry points, graph definitions, configuration modules, client initialization and dependency metadata.
- [x] Inspect original environment variable names without exposing secret values.
- [x] Check installed Python, Docker, model paths and service sockets.
- [x] Record all required, optional and unused settings in `docs/CONFIGURATION.md`.

### Task 2: Faithful source migration and local setup

- [x] Copy `app/`, `prompts/`, `test/`, `pyproject.toml` and `uv.lock` from `../掌柜智库RAG项目/code_PythonProject16/`.
- [x] Add `.gitignore`, `.env.example`, local `.env`, `README.md` and `NOTICE.md`; keep secrets out of tracked templates.
- [x] Add `compose.yaml` for the local databases and object storage, with persistent volumes and loopback host ports.
- [x] Create an isolated `.venv` with Python 3.12 and install dependencies using uv; record any reproducible compatibility issue.

### Task 3: Startup verification and handoff

- [x] Attempt Docker engine startup; engine unavailable, user chose existing remote services, so no containers deployed.
- [x] Run both FastAPI entry points and request their HTML pages and OpenAPI endpoints when dependencies permit.
- [x] Resolve only reproduced startup failures; no source changes needed after dependency installation.
- [x] Compare migrated source against upstream and scan deliverable files for inherited secrets.
- [x] Run syntax/configuration checks and document verified results and remaining inputs in `docs/STARTUP_STATUS.md`.
- [x] Complete model downloads and exercise actual embedding and reranking locally.
- [x] Give the user a concise configuration checklist and the exact file to fill in. Do not claim end-to-end success without a real import and answer.

## Deferred until user inputs arrive

- [x] User chose Windows-local Docker services and supplied personal API credentials; verified them and restarted both APIs (import 8002, query 8001).
- [x] Verify real PDF ingestion, persistent storage, retrieval, image links, streaming and non-streaming answers, follow-up history and unmatched/clarification branches end to end. Evidence: `docs/E2E_VALIDATION.md`.
