[CmdletBinding()]
param(
    [ValidateSet("private", "public")]
    [string]$Visibility = "private",
    [string]$RepositoryName = "LTM_project_2",
    [string]$CommitMessage = "Initial commit: Cloud FinOps remediation agent"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path -LiteralPath ".").Path
Write-Host "Project root: $projectRoot" -ForegroundColor Cyan

$requiredFiles = @(
    "app.py",
    "README.md",
    ".gitignore",
    ".env.example",
    "requirements.txt",
    "synthetic_data\resources.json",
    "policies\finops_rules.yaml",
    "expected_findings\expected_findings.json",
    "templates\terraform\downsize_proposal.tf.j2",
    "templates\terraform\archive_proposal.tf.j2",
    "finops_project_master_context_revised.txt",
    "archive\finops_project_master_context.txt",
    "DANIELROBIN_T9925_REVIEW0.pptx",
    "DANIELROBIN_T9925_REVIEW1.pptx",
    "DANIELROBIN_T9925_REVIEW2.pptx",
    "DANIELROBIN_T9925_REVIEW3.pptx"
)

$missingFiles = @(
    foreach ($relativePath in $requiredFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $relativePath) -PathType Leaf)) {
            $relativePath
        }
    }
)

if ($missingFiles.Count -gt 0) {
    Write-Host "Missing required repository files:" -ForegroundColor Red
    $missingFiles | ForEach-Object { Write-Host "  - $_" }
    throw "Repository preparation stopped because required files are missing."
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or is not available on PATH."
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is not installed or is not available on PATH."
}

Write-Host "`nChecking GitHub CLI authentication..." -ForegroundColor Cyan
& gh auth status
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI is not authenticated. Run: gh auth login"
}

if (Test-Path -LiteralPath ".\security-review.ps1" -PathType Leaf) {
    Write-Host "`nRunning source security review..." -ForegroundColor Cyan
    & .\security-review.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "Security review failed. Resolve the findings before publishing."
    }
}

if (-not (Test-Path -LiteralPath ".\.git" -PathType Container)) {
    Write-Host "`nInitializing Git repository..." -ForegroundColor Cyan
    & git init -b main
    if ($LASTEXITCODE -ne 0) {
        throw "git init failed."
    }
} else {
    Write-Host "`nExisting local Git repository detected." -ForegroundColor Yellow
    & git branch -M main
}

$existingOrigin = & git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($existingOrigin)) {
    throw "An origin remote already exists: $existingOrigin. Review it before creating a new repository."
}

Write-Host "`nChecking that essential files are not ignored..." -ForegroundColor Cyan
$mustTrack = @(
    "synthetic_data\resources.json",
    "policies\finops_rules.yaml",
    "expected_findings\expected_findings.json",
    "templates\terraform\downsize_proposal.tf.j2",
    "finops_project_master_context_revised.txt",
    "archive\finops_project_master_context.txt",
    "DANIELROBIN_T9925_REVIEW0.pptx",
    "DANIELROBIN_T9925_REVIEW1.pptx",
    "DANIELROBIN_T9925_REVIEW2.pptx",
    "DANIELROBIN_T9925_REVIEW3.pptx"
)

$ignoredImportantFiles = @(
    foreach ($path in $mustTrack) {
        & git check-ignore -q -- $path
        if ($LASTEXITCODE -eq 0) {
            $path
        }
    }
)

if ($ignoredImportantFiles.Count -gt 0) {
    Write-Host "Important files are incorrectly ignored:" -ForegroundColor Red
    $ignoredImportantFiles | ForEach-Object { Write-Host "  - $_" }
    throw "Correct .gitignore before publishing."
}

Write-Host "`nStaging repository files..." -ForegroundColor Cyan
& git add --all
if ($LASTEXITCODE -ne 0) {
    throw "git add failed."
}

$forbiddenStagedPatterns = @(
    '(^|/)\.env$',
    '(^|/)\.venv/',
    '(^|/)\.checkov-venv/',
    '(^|/)output/',
    '(^|/)\.terraform/',
    '\.tfstate($|\.)',
    '\.tfplan$',
    '(^|/)copilot files/',
    '(^|/)session[^/]*-extracted/'
)

$stagedFiles = @(& git diff --cached --name-only)
$forbiddenStagedFiles = @(
    foreach ($file in $stagedFiles) {
        foreach ($pattern in $forbiddenStagedPatterns) {
            if ($file -match $pattern) {
                $file
                break
            }
        }
    }
)

if ($forbiddenStagedFiles.Count -gt 0) {
    Write-Host "Forbidden generated or sensitive files were staged:" -ForegroundColor Red
    $forbiddenStagedFiles | Sort-Object -Unique | ForEach-Object { Write-Host "  - $_" }
    & git reset
    throw "Staging was reset. Correct .gitignore and try again."
}

Write-Host "`nStaged files:" -ForegroundColor Cyan
$stagedFiles | ForEach-Object { Write-Host "  $($_)" }
Write-Host "`nTotal staged files: $($stagedFiles.Count)" -ForegroundColor Green

$requiredStagedFiles = @(
    "synthetic_data/resources.json",
    "policies/finops_rules.yaml",
    "expected_findings/expected_findings.json",
    "templates/terraform/downsize_proposal.tf.j2",
    "templates/terraform/archive_proposal.tf.j2",
    "finops_project_master_context_revised.txt",
    "archive/finops_project_master_context.txt",
    "DANIELROBIN_T9925_REVIEW0.pptx",
    "DANIELROBIN_T9925_REVIEW1.pptx",
    "DANIELROBIN_T9925_REVIEW2.pptx",
    "DANIELROBIN_T9925_REVIEW3.pptx"
)

$missingFromStage = @(
    foreach ($path in $requiredStagedFiles) {
        if ($stagedFiles -notcontains $path) {
            $path
        }
    }
)

if ($missingFromStage.Count -gt 0) {
    Write-Host "Required files are absent from staging:" -ForegroundColor Red
    $missingFromStage | ForEach-Object { Write-Host "  - $_" }
    & git reset
    throw "Staging was reset because important files were missing."
}

Write-Host "`nCreating initial commit..." -ForegroundColor Cyan
& git commit -m $CommitMessage
if ($LASTEXITCODE -ne 0) {
    throw "git commit failed. Configure git user.name and user.email if requested."
}

$visibilityFlag = if ($Visibility -eq "public") { "--public" } else { "--private" }

Write-Host "`nCreating GitHub repository '$RepositoryName' as $Visibility..." -ForegroundColor Cyan
& gh repo create $RepositoryName `
    $visibilityFlag `
    --description "Safety-first synthetic multi-cloud FinOps remediation planning agent" `
    --source "." `
    --remote "origin" `
    --push

if ($LASTEXITCODE -ne 0) {
    throw "GitHub repository creation or initial push failed."
}

Write-Host "`nRepository created and pushed successfully." -ForegroundColor Green
& git status
& git remote -v
& gh repo view --web
