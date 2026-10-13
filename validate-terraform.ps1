[CmdletBinding()]
param(
    [string]$TerraformExecutable = "C:\Users\T9925\Tools\Terraform\terraform.exe",
    [string]$TFLintExecutable = "C:\Users\T9925\Tools\TFLint\tflint.exe",
    [string]$TerraformOutputDirectory = ".\output\terraform",
    [string]$ReportOutputDirectory = ".\output\reports",
    [int]$ExpectedArtifactCount = 5
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-VisibleCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Executable,

        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [string[]]$Arguments
    )

    & $Executable @Arguments | Out-Host
    return $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $TerraformExecutable -PathType Leaf)) {
    throw "Terraform executable was not found: $TerraformExecutable"
}

if (-not (Test-Path -LiteralPath $TFLintExecutable -PathType Leaf)) {
    throw "TFLint executable was not found: $TFLintExecutable"
}

if (-not (Test-Path -LiteralPath $TerraformOutputDirectory -PathType Container)) {
    throw "Terraform output directory was not found: $TerraformOutputDirectory"
}

$manifestPath = Join-Path $TerraformOutputDirectory "artifact_manifest.json"

if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Artifact manifest was not found: $manifestPath"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json

if ($manifest.execution_enabled -ne $false) {
    throw "Artifact manifest must state execution_enabled=false."
}

if ($manifest.dry_run -ne $true) {
    throw "Artifact manifest must state dry_run=true."
}

$directories = @(
    Get-ChildItem -LiteralPath $TerraformOutputDirectory -Directory |
        Sort-Object Name
)

if ($directories.Count -ne $ExpectedArtifactCount) {
    throw "Expected $ExpectedArtifactCount artifact directories but found $($directories.Count)."
}

$results = [System.Collections.Generic.List[object]]::new()

foreach ($directory in $directories) {
    Write-Host "`n=== Validating $($directory.Name) ===" -ForegroundColor Cyan

    $proposalFiles = @(
        Get-ChildItem -LiteralPath $directory.FullName -Filter "*.tf" -File
    )

    if ($proposalFiles.Count -ne 1) {
        throw "Expected one .tf proposal in $($directory.Name), found $($proposalFiles.Count)."
    }

    $proposalPath = $proposalFiles[0].FullName
    $manifestEntry = @(
        $manifest.artifacts |
            Where-Object { $_.resource_id -eq $directory.Name }
    )

    if ($manifestEntry.Count -ne 1) {
        throw "Expected one manifest entry for $($directory.Name)."
    }

    $generationHash = $manifestEntry[0].sha256.ToLowerInvariant()
    $preFormatHash = (Get-FileHash -LiteralPath $proposalPath -Algorithm SHA256).Hash.ToLowerInvariant()

    $fmtExitCode = Invoke-VisibleCommand `
        -Executable $TerraformExecutable `
        -Arguments @("-chdir=$($directory.FullName)", "fmt")

    if ($fmtExitCode -ne 0) {
        throw "Terraform fmt failed for $($directory.Name). Exit code: $fmtExitCode"
    }

    $postFormatHash = (Get-FileHash -LiteralPath $proposalPath -Algorithm SHA256).Hash.ToLowerInvariant()

    $fmtCheckExitCode = Invoke-VisibleCommand `
        -Executable $TerraformExecutable `
        -Arguments @("-chdir=$($directory.FullName)", "fmt", "-check")
    $fmtPassed = $fmtCheckExitCode -eq 0

    $initExitCode = Invoke-VisibleCommand `
        -Executable $TerraformExecutable `
        -Arguments @(
            "-chdir=$($directory.FullName)",
            "init",
            "-backend=false",
            "-input=false"
        )
    $initPassed = $initExitCode -eq 0

    $validatePassed = $false

    if ($initPassed) {
        $terraformValidateJson = & $TerraformExecutable `
            "-chdir=$($directory.FullName)" `
            validate `
            -json `
            2>&1 | Out-String

        $validateExitCode = $LASTEXITCODE

        if ($validateExitCode -eq 0) {
            try {
                $validatePayload = $terraformValidateJson | ConvertFrom-Json
                $validatePassed = $validatePayload.valid -eq $true
            }
            catch {
                Write-Warning "Could not parse Terraform validation JSON for $($directory.Name)."
                $validatePassed = $false
            }
        }
    }

    Push-Location $directory.FullName

    try {
        $tflintExitCode = Invoke-VisibleCommand `
            -Executable $TFLintExecutable `
            -Arguments @()
        $tflintPassed = $tflintExitCode -eq 0
    }
    finally {
        Pop-Location
    }

    $content = Get-Content -LiteralPath $proposalPath -Raw
    $dryRunPresent = $content -match 'dry_run\s*=\s*true'
    $approvalPresent = $content -match 'human_approval_required\s*=\s*true'

    $unsafePatterns = @(
        'resource\s+"',
        'module\s+"',
        'provider\s+"',
        'local-exec',
        'remote-exec',
        'terraform\s+apply',
        'terraform\s+destroy'
    )

    $unsafeMatches = @(
        foreach ($pattern in $unsafePatterns) {
            if ($content -match $pattern) {
                $pattern
            }
        }
    )

    $unsafeContentFound = $unsafeMatches.Count -gt 0
    $safetyPassed = $dryRunPresent -and $approvalPresent -and (-not $unsafeContentFound)
    $overallPassed = $fmtPassed -and $initPassed -and $validatePassed -and $tflintPassed -and $safetyPassed

    $result = [PSCustomObject]@{
        ResourceDirectory = $directory.Name
        ProposalPath = $proposalPath
        TerraformFmt = [bool]$fmtPassed
        TerraformInit = [bool]$initPassed
        TerraformValidate = [bool]$validatePassed
        TFLint = [bool]$tflintPassed
        DryRunPresent = [bool]$dryRunPresent
        ApprovalRequiredPresent = [bool]$approvalPresent
        UnsafeContentFound = [bool]$unsafeContentFound
        GenerationSha256 = $generationHash
        PreFormatSha256 = $preFormatHash
        PostFormatSha256 = $postFormatHash
        GenerationHashMatchedBeforeFormat = [bool]($generationHash -eq $preFormatHash)
        FormattingChangedFile = [bool]($preFormatHash -ne $postFormatHash)
        OverallPassed = [bool]$overallPassed
    }

    $results.Add($result)
}

if ($results.Count -ne $ExpectedArtifactCount) {
    throw "Expected $ExpectedArtifactCount validation results but found $($results.Count)."
}

New-Item -ItemType Directory -Path $ReportOutputDirectory -Force | Out-Null

$jsonPath = Join-Path $ReportOutputDirectory "terraform_validation_results.json"
$csvPath = Join-Path $ReportOutputDirectory "terraform_validation_results.csv"

$results |
    ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath $jsonPath -Encoding utf8

$results |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding utf8

$results |
    Format-Table `
        ResourceDirectory, `
        TerraformFmt, `
        TerraformInit, `
        TerraformValidate, `
        TFLint, `
        OverallPassed `
        -AutoSize

$failed = @(
    $results |
        Where-Object { $_.OverallPassed -ne $true }
)

Write-Host "`nJSON evidence: $jsonPath"
Write-Host "CSV evidence: $csvPath"

if ($failed.Count -gt 0) {
    Write-Host "`nThe following proposal directories failed:" -ForegroundColor Red
    $failed |
        Format-Table `
            ResourceDirectory, `
            TerraformFmt, `
            TerraformInit, `
            TerraformValidate, `
            TFLint, `
            DryRunPresent, `
            ApprovalRequiredPresent, `
            UnsafeContentFound, `
            OverallPassed `
            -AutoSize

    Write-Host "`nTerraform proposal validation failed." -ForegroundColor Red
    exit 1
}

Write-Host "`nAll review-only proposals passed validation." -ForegroundColor Green
exit 0
