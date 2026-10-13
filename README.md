# Autonomous Cloud FinOps Remediation Agent

A safety-first, policy-driven demonstration that analyzes synthetic AWS-style and Azure-style cloud telemetry, identifies cost-optimization opportunities, protects sensitive resources, calculates illustrative savings, and generates review-only Terraform proposal artifacts for human review.

> **Repository name:** `LTM_project_2`  
> **Project status:** Demonstration complete through validation and reporting  
> **Scope:** Synthetic, local, non-production, and non-destructive

## Project Overview

Cloud environments can accumulate underutilized compute instances, unattached storage, old snapshots, and unused network resources. Manual reviews are time-consuming and can create risk when ownership, environment, or business-criticality information is incomplete.

This project demonstrates a controlled FinOps workflow that:

1. Loads normalized synthetic AWS-style and Azure-style telemetry.
2. Validates telemetry and policy files using typed Pydantic models.
3. Applies explicit safety gates before optimization rules.
4. Evaluates resources using deterministic Python logic.
5. Calculates transparent illustrative savings.
6. Produces structured findings and portfolio reports.
7. Displays results in an interactive Streamlit dashboard.
8. Generates allow-listed, review-only Terraform proposal artifacts.
9. Validates proposal formatting, syntax, linting, safety declarations, and checksums.

The application does not connect to live AWS or Azure accounts, use cloud credentials, execute `terraform apply`, or modify infrastructure.

## Key Results

The current synthetic dataset produces the following deterministic results:

- **24** total synthetic resources analyzed
- **5** `WASTE_DETECTED` findings
- **6** protected resources
- **6** findings requiring human review
- **2** findings with insufficient observation data
- **5** resources with no waste detected
- **USD 153.50** confirmed illustrative monthly savings
- **USD 1,842.00** confirmed illustrative annual savings
- **USD 4.00** potential monthly savings pending review
- **5** eligible review-only Terraform proposal artifacts

Confirmed savings include only `WASTE_DETECTED` findings. Potential savings associated with `REVIEW_REQUIRED` findings remain separate.

## Safety-First Design

Safety checks always run before cost optimization.

The application protects or escalates resources when:

- The resource is production or business-critical.
- A legal hold applies.
- An explicit FinOps exemption exists.
- Ownership information is missing.
- The environment is unknown or conflicts with tags.
- The observation period is too short.
- The calculated saving is zero.

Protected resources receive `NO_ACTION`. Missing or ambiguous governance information produces `REVIEW_REQUIRED`. All material recommendations require human approval.

## Architecture

```text
Synthetic telemetry JSON
        |
        v
Pydantic input validation
        |
        v
Versioned YAML policy validation
        |
        v
Safety gates
        |
        v
Deterministic policy evaluation
        |
        v
Savings calculation
        |
        v
Structured findings
        |
        +---------------------------+
        |                           |
        v                           v
Portfolio reports            Streamlit dashboard
        |                           |
        v                           v
JSON and CSV exports      Human review and filtering
        |
        v
Allow-listed Jinja2 templates
        |
        v
Review-only Terraform proposals
        |
        v
Terraform format, validate, TFLint,
safety scan, and checksum evidence
```

## Dataset

The primary dataset is stored at:

```text
synthetic_data/resources.json
```

It contains **24 normalized synthetic resource records**:

- 13 AWS-style resources
- 11 Azure-style resources
- 11 compute instances
- 6 storage volumes
- 5 snapshots
- 2 public IP resources

### Scenario coverage

The dataset includes:

- Idle and healthy compute instances
- Exact CPU threshold boundaries
- Exact observation-window boundaries
- Production and critical resources
- Explicit exemptions and legal holds
- Missing ownership
- Unknown and conflicting environments
- Attached and unattached storage
- Recently detached storage
- Old, recent, referenced, and unreferenced snapshots
- Unassociated public IPs
- Zero-savings outcomes

The JSON is a normalized FinOps telemetry model, not a raw AWS or Azure log export. A future implementation could populate the same schema using read-only cloud inventory, monitoring, tagging, and cost APIs.

## Policies and Safety Gates

Policies are stored at:

```text
policies/finops_rules.yaml
```

### Optimization policies

#### `FINOPS-COMPUTE-001`: Idle compute

- CPU utilization at or below 3%
- Minimum observation period of 14 days
- Recommended action: `DOWNSIZE`

#### `FINOPS-STORAGE-001`: Unattached storage

- Storage must be unattached
- Minimum unattached observation period of 14 days
- Recommended action: `ARCHIVE`

#### `FINOPS-SNAPSHOT-001`: Old unreferenced snapshot

- Minimum age of 90 days
- Snapshot must be unreferenced
- Recommended action: `ARCHIVE`

#### `FINOPS-IP-001`: Unassociated public IP

- IP must be unattached and unreferenced
- Outcome: `REVIEW_REQUIRED`

### Safety gates

- `SAFETY-001`: production, critical, or legal-hold protection
- `SAFETY-002`: explicit exemption protection
- `SAFETY-003`: missing-owner escalation
- `SAFETY-004`: unknown or conflicting environment escalation

The YAML `when` fields are descriptive. They are never executed dynamically. Safety behavior is implemented explicitly in Python.

## Findings and Ground Truth

Expected findings are stored at:

```text
expected_findings/expected_findings.json
```

The deterministic engine compares all 24 calculated findings with this ground-truth fixture. Regression checks cover:

- Matched policy
- Finding status
- Recommended action
- Monthly and annual savings
- Protection state
- Human-approval requirement
- Terraform artifact eligibility

## Streamlit Dashboard

The dashboard is implemented in:

```text
app.py
```

### Dashboard capabilities

- Input-readiness validation
- Portfolio cost and savings metrics
- Confirmed and pending-review savings separation
- Filters for provider, resource type, status, action, and protection
- Prioritized cost-saving recommendations
- Savings breakdown by cloud, resource type, and action
- Complete deterministic findings table
- Finding-status distribution
- JSON and CSV downloads
- Explicit review-only Terraform proposal generation
- Artifact manifest display
- Terraform validation evidence display

Start the dashboard with:

```powershell
python -m streamlit run .\app.py
```

The application normally opens at `http://localhost:8501`.

## Reporting

The reporting module is:

```text
finops_demo/reporting.py
```

Generate reports with:

```powershell
python .\generate_report.py
```

Generated files:

```text
output/reports/finops_review_report.json
output/reports/finops_review_report.csv
```

Reports include:

- Dataset and policy metadata
- Synthetic-data disclaimer
- Portfolio totals
- Status distribution
- Confirmed savings
- Potential savings pending review
- Savings by provider, resource type, and action
- Prioritized recommendations
- All findings

## Review-Only Terraform Proposals

The proposal compiler is:

```text
finops_demo/remediation_compiler.py
```

Templates are stored in:

```text
templates/terraform/downsize_proposal.tf.j2
templates/terraform/archive_proposal.tf.j2
```

Generate proposals with:

```powershell
python .\generate_artifacts.py
```

Generated structure:

```text
output/terraform/
|-- artifact_manifest.json
|-- aws-dev-ec2-001/
|   `-- downsize_proposal.tf
|-- aws-dev-ec2-022/
|   `-- downsize_proposal.tf
|-- aws-dev-snap-014/
|   `-- archive_proposal.tf
|-- aws-dev-vol-009/
|   `-- archive_proposal.tf
`-- azure-dev-vm-002/
    `-- downsize_proposal.tf
```

### Allow-listed combinations

- `compute_instance + DOWNSIZE`
- `storage_volume + ARCHIVE`
- `snapshot + ARCHIVE`

### Artifact safeguards

- Only eligible `WASTE_DETECTED` findings can generate proposals.
- Protected and review-required findings are rejected.
- Every proposal has `dry_run = true`.
- Every proposal has `human_approval_required = true`.
- The manifest states `execution_enabled = false`.
- Safe resource-directory names prevent path traversal.
- SHA-256 values record artifact integrity.
- Forbidden-content scans reject operational or destructive content.
- Generated files contain no provider, resource, module, or provisioner blocks.

These files are Terraform-formatted recommendation documents, not real Terraform plans. They cannot modify infrastructure.

## Terraform Validation

Terraform and TFLint validation is automated through:

```text
validate-terraform.ps1
```

Run:

```powershell
.\validate-terraform.ps1
```

The script performs:

- `terraform fmt`
- `terraform fmt -check`
- `terraform init -backend=false -input=false`
- `terraform validate -json`
- TFLint
- Dry-run declaration checks
- Human-approval declaration checks
- Unsafe-content scanning
- Generation, pre-format, and post-format SHA-256 recording

Generated evidence:

```text
output/reports/terraform_validation_results.json
output/reports/terraform_validation_results.csv
```

Terraform validation checks formatting and internal configuration consistency. It does not validate a real cloud deployment.

## Project Structure

```text
LTM_project_2/
|-- app.py
|-- analyze_inputs.py
|-- generate_artifacts.py
|-- generate_report.py
|-- validate_inputs.py
|-- validate-terraform.ps1
|-- security-review.ps1
|-- setup-tools.ps1
|-- README.md
|-- requirements.txt
|-- requirements-full.txt
|-- dataset_summary.json
|-- synthetic_data/
|   `-- resources.json
|-- policies/
|   `-- finops_rules.yaml
|-- expected_findings/
|   `-- expected_findings.json
|-- templates/
|   `-- terraform/
|       |-- archive_proposal.tf.j2
|       `-- downsize_proposal.tf.j2
|-- finops_demo/
|   |-- loaders.py
|   |-- models.py
|   |-- policy_engine.py
|   |-- remediation_compiler.py
|   |-- reporting.py
|   `-- mock_data.py
|-- tests/
|   |-- test_input_validation.py
|   |-- test_mock_data.py
|   |-- test_policy_engine.py
|   |-- test_remediation_compiler.py
|   |-- test_reporting.py
|   `-- test_validation_evidence.py
|-- documentation and context files
`-- presentation files
```

`mock_data.py` and its tests are retained as legacy Session 1 fixtures. The main dashboard uses deterministic engine findings.

## Prerequisites

- Windows 10 or Windows 11
- Python 3.12
- PowerShell
- Terraform CLI
- TFLint
- Git

Terraform and TFLint are used only for local proposal validation.

## Installation

### 1. Clone the repository

```powershell
git clone https://github.com/dr0b1n/LTM_project_2.git
Set-Location .\LTM_project_2
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate it

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r .\requirements.txt
```

If the repository includes a broader development dependency file, use it only when required:

```powershell
python -m pip install -r .\requirements-full.txt
```

### 5. Check dependencies

```powershell
python -m pip check
```

Expected:

```text
No broken requirements found.
```

### 6. Configure Terraform and TFLint

If `setup-tools.ps1` matches the local machine paths:

```powershell
.\setup-tools.ps1
```

Otherwise, pass explicit executable paths to the validation script:

```powershell
.\validate-terraform.ps1 `
    -TerraformExecutable "C:\path\to\terraform.exe" `
    -TFLintExecutable "C:\path\to\tflint.exe"
```

## Run the End-to-End Workflow

Run the commands from the repository root in this order:

```powershell
python .\validate_inputs.py
python .\analyze_inputs.py
python .\generate_report.py
python .\generate_artifacts.py
.\validate-terraform.ps1
python -m pytest .\tests -v
python -m streamlit run .\app.py
```

### Expected validation totals

```text
Validated resources: 24
Validated optimization policies: 4
Validated safety gates: 4
```

### Expected finding totals

```text
WASTE_DETECTED: 5
PROTECTED: 6
REVIEW_REQUIRED: 6
INSUFFICIENT_DATA: 2
NO_WASTE_DETECTED: 5
```

### Expected artifact totals

```text
Eligible findings: 5
Artifacts generated: 5
Execution enabled: False
```

## Tests and Code Quality

Run all tests:

```powershell
python -m pytest .\tests -v
```

Run Ruff against active project source:

```powershell
python -m ruff check `
    .\app.py `
    .\validate_inputs.py `
    .\analyze_inputs.py `
    .\generate_report.py `
    .\generate_artifacts.py `
    .\finops_demo `
    .\tests
```

Compile Python files:

```powershell
python -m compileall -q `
    .\app.py `
    .\validate_inputs.py `
    .\analyze_inputs.py `
    .\generate_report.py `
    .\generate_artifacts.py `
    .\finops_demo `
    .\tests
```

Check installed dependencies:

```powershell
python -m pip check
```

### Test coverage areas

- Telemetry and policy validation
- Invalid costs and timestamps
- Duplicate resource IDs
- Record-count mismatches
- Safety-gate precedence
- Missing-owner escalation
- Threshold boundaries
- Zero-savings behavior
- Ground-truth regression comparison
- Portfolio reporting
- Savings separation
- Priority ordering
- JSON and CSV serialization
- Artifact eligibility
- Protected and review-required rejection
- Safe artifact paths
- Terraform validation evidence

## Security Review

Run the local source review:

```powershell
.\security-review.ps1
```

The script searches source files for:

- Common credential-like patterns
- Private-key headers
- Unsafe Terraform command text

Potential matches require human review because documentation and test fixtures can contain safe placeholder text.

Never commit:

- Cloud credentials
- `.env` files containing secrets
- Private keys
- Terraform state
- Terraform plan files
- Virtual environments
- Generated output

## Git and Repository Guidance

The repository should include:

- Python source code
- PowerShell utility scripts
- Synthetic datasets
- YAML policies
- Expected findings
- Jinja2 templates
- Tests
- README and supporting documentation
- Master project context files
- PowerPoint project presentation files

The repository should exclude:

```text
.venv/
.checkov-venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.env
output/
.terraform/
*.tfstate
*.tfstate.*
*.tfplan
session*-extracted/
*.zip
```

Before committing, confirm important source data is not ignored:

```powershell
git check-ignore -v `
    .\synthetic_data\resources.json `
    .\policies\finops_rules.yaml `
    .\expected_findings\expected_findings.json `
    .\templates\terraform\downsize_proposal.tf.j2
```

Expected: no output.

## GitHub Actions

GitHub Actions can be added for continuous integration and reproducibility. A suitable workflow can:

- Install Python dependencies
- Run Ruff
- Validate inputs
- Run the deterministic engine
- Generate reports
- Generate proposal artifacts
- Run Pytest
- Validate Terraform proposal syntax
- Upload reports and validation evidence as workflow artifacts

GitHub Actions should be described as CI and validation automation, not as persistent Streamlit hosting. The current application deployment is local.

## Current Deployment

The current demonstration runs locally on a Windows system:

```text
Browser
   |
   v
Local Streamlit server
   |
   v
Python validation, policy, reporting, and proposal modules
   |
   v
Local JSON, YAML, reports, and Terraform proposal files
   |
   v
Local Terraform CLI and TFLint validation
```

The application is not currently hosted on AWS, Azure, GitHub Pages, or a production server.

## Agentic Characteristics

The project follows a constrained agent-style workflow:

```text
Observe -> Validate -> Analyze -> Decide -> Generate -> Validate -> Report
```

It is not a fully autonomous LLM agent. The core decision path is deterministic and policy-driven. The application does not dynamically plan, learn, or execute cloud changes. Its permitted actions are limited to producing findings, reports, and review-only artifacts.

A precise description is:

> A safety-constrained, policy-driven Cloud FinOps recommendation and remediation-planning agent.

## Demonstration Walkthrough

A concise demonstration can follow this sequence:

1. Show the 24-record synthetic dataset.
2. Explain the four policies and four safety gates.
3. Run input validation.
4. Show the deterministic finding distribution.
5. Open Streamlit and review portfolio savings.
6. Filter protected and review-required resources.
7. Show prioritized recommendations.
8. Generate reports.
9. Generate five review-only Terraform proposals.
10. Show the artifact manifest and validation evidence.
11. Reiterate that no live cloud resource was accessed or modified.

## Limitations

- Synthetic telemetry only
- Synthetic and illustrative costs
- No live AWS or Azure connectors
- No authoritative cloud-pricing integration
- No real Terraform execution plan
- No `terraform apply`
- No automatic cloud remediation
- No production authentication or authorization
- No persistent database
- No enterprise approval workflow
- No scheduler or background agent
- Not production-ready

## Future Work

Potential extensions include:

- Approved read-only AWS and Azure collectors
- Cloud-native monitoring and cost API integration
- Authoritative pricing sources
- Additional policies and resource types
- Enterprise approval and ticketing integration
- Centralized audit storage
- Controlled, organization-approved Terraform modules
- Containerized internal deployment
- GitHub Actions continuous integration
- Optional AI-generated summaries outside the decision path

## Responsible Use

This project is designed for education and demonstration. Recommendations must be reviewed by a human with appropriate cloud, financial, governance, and security context. Savings are illustrative and should not be treated as guaranteed financial outcomes.

## Presentation and Context Files

The repository may include master project context files and PowerPoint presentations used for project review. These materials document the design, implemented state, methodology, results, limitations, and future work. They must not contain credentials, confidential tenant information, or personal data.

## License

No license has been selected for this repository. Add an appropriate license only after confirming project-sharing requirements with the project owner or organization.

## Acknowledgements

Thanks to the project mentor, classroom coordinators, reviewers, and peers who provided guidance and feedback throughout development.
