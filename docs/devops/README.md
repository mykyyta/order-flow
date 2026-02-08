# DevOps Docs

Entry points:
- Infrastructure overview: `docs/devops/infrastructure_overview.md`
- Runbook: `docs/devops/runbook.md`
- Brownfield Terraform adoption: `docs/devops/terraform_brownfield_migration.md`
- Notes / next steps: `docs/devops/future_devops_notes.md`

Related:
- Terraform root module: `infra/environments/prod`
- GitHub Actions workflows: `.github/workflows`
- Options:
  - Fast deploy: push to `main` (no migrations)
  - Full deploy: run `deploy.yml` manually with inputs (migrations + job image sync)
  - PR bypass: add label `skip-lint` to skip Ruff
