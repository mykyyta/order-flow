# Terraform Brownfield Adoption (GCP)

This repo is adopting Terraform for existing GCP resources (import-first), with drift protection during the transition.

## Principles
- Import existing resources into state before attempting to “fix” drift.
- Use `lifecycle.ignore_changes` during the initial adoption, then narrow it gradually once plans are stable.
- Keep secrets out of git history.

## Prod root module
- Terraform root: `infra/environments/prod`
- Helper script for initial imports: `infra/environments/prod/import_existing.sh`

## Typical flow (prod)
1. Ensure your backend config exists:
   - `infra/environments/prod/backend.hcl` (bucket + prefix)
2. Ensure `infra/environments/prod/terraform.tfvars` is present and matches the existing resource names.
3. Run the import helper:
   ```bash
   cd infra/environments/prod
   ./import_existing.sh
   ```
4. Confirm `terraform plan` is stable (ideally no changes) before narrowing `ignore_changes`.

## After import: narrowing `ignore_changes`
Once stable, change `ignore_changes = all` to only ignore the specific fields you still want controlled outside Terraform (usually just the image), and repeat plan/apply carefully.
