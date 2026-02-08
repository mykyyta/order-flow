# Future DevOps Notes (Simple Path)

## 1) Staging without heavy complexity
Goal: add `staging` safely with minimum duplication.

### Recommended structure
- Keep one reusable Terraform module for the app stack.
- Use two lightweight environment wrappers:
  - `infra/environments/prod`
  - `infra/environments/staging`
- Differences go to `terraform.tfvars` only (names, limits, secrets, DB URL, project).

### Why
- Less copy/paste.
- Fewer config drifts between `prod` and `staging`.
- Easier reviews and safer changes.

## 2) Minimal rollout strategy
Current practical flow is good:
Fast path (default on push to `main`):
1. Deploy Cloud Run service image.

Full deploy (manual, when schema changes):
1. Update migrate job image.
2. Run migrate job.
3. Deploy Cloud Run service image.

Infra changes remain separate:
1. Terraform apply when infra changes are merged.

Keep this flow until Cloud Run resources are fully removed from Terraform adoption mode.

## 3) Practical next improvements (no fanaticism)
1. Add a tiny smoke check step in CI after deploy (HTTP 200 + migrate job success).
2. Add one scheduled backup/export check for DB (or at least restore drill notes).
3. Add one alert channel (Cloud Run errors + failed job executions).
4. Pin and update dependencies monthly (Python packages + Terraform provider).
5. Keep one-page runbook updated whenever deploy flow changes.

## 4) When to invest more
Only after stable routine deployments:
- promote to module-based Terraform stack,
- stricter environment protections,
- optional pre-deploy migration strategy (migrate before traffic switch).
