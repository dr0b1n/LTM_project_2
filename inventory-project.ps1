[CmdletBinding()]
param(
    [string]$ProjectRoot = ".",
    [string]$TextReport = ".\project-file-inventory.txt",
    [string]$CsvReport = ".\project-file-inventory.csv"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path -LiteralPath $ProjectRoot).Path

$excludedDirectories = @(
    ".git",
    ".venv",
    ".checkov-venv",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "__pycache__",
    ".terraform",
    "node_modules",
    "output",
    "old versions",
    "tool-smoke-test"
)

$excludedFilePatterns = @(
    "*.pyc",
    "*.pyo",
    "*.tmp",
    "*.log",
    "*.tfstate",
    "*.tfstate.*",
    "*.tfplan"
)

$files = @(
    Get-ChildItem -LiteralPath $root -Recurse -File -Force |
        Where-Object {
            $file = $_
            $relativePath = $file.FullName.Substring($root.Length).TrimStart([char[]]"\/")
            $parts = $relativePath -split "[\\/]"
            $excludeDirectory = $false
            $excludeFile = $false

            foreach ($part in $parts) {
                if ($excludedDirectories -contains $part) {
                    $excludeDirectory = $true
                    break
                }

                if ($part -like "session*-extracted") {
                    $excludeDirectory = $true
                    break
                }
            }

            foreach ($pattern in $excludedFilePatterns) {
                if ($file.Name -like $pattern) {
                    $excludeFile = $true
                    break
                }
            }

            -not $excludeDirectory -and -not $excludeFile
        }
)

$inventory = @(
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($root.Length).TrimStart([char[]]"\/")
        $extension = $file.Extension

        if ([string]::IsNullOrWhiteSpace($extension)) {
            $extension = "[no extension]"
        }

        $category = switch -Regex ($relativePath) {
            '^synthetic_data[\\/]' { "Synthetic data"; break }
            '^policies[\\/]' { "Policies"; break }
            '^expected_findings[\\/]' { "Expected findings"; break }
            '^templates[\\/]' { "Templates"; break }
            '^tests[\\/]' { "Tests"; break }
            '\.pptx$' { "PowerPoint"; break }
            '(?i)(context|master).*\.(txt|md)$' { "Project context"; break }
            '\.(py|ps1)$' { "Source code"; break }
            '\.(md|txt)$' { "Documentation"; break }
            default { "Other" }
        }

        [PSCustomObject]@{
            Category = $category
            RelativePath = $relativePath
            Extension = $extension.ToLowerInvariant()
            SizeBytes = $file.Length
            SizeKB = [math]::Round($file.Length / 1KB, 2)
            LastModified = $file.LastWriteTime
        }
    }
)

$inventory = @($inventory | Sort-Object RelativePath)

$summary = @(
    $inventory |
        Group-Object Category |
        ForEach-Object {
            $totalBytes = ($_.Group | Measure-Object -Property SizeBytes -Sum).Sum

            [PSCustomObject]@{
                Category = $_.Name
                FileCount = $_.Count
                TotalSizeKB = [math]::Round($totalBytes / 1KB, 2)
            }
        } |
        Sort-Object Category
)

$expectedFiles = @(
    "app.py",
    "README.md",
    ".gitignore",
    "requirements.txt",
    "synthetic_data\resources.json",
    "policies\finops_rules.yaml",
    "expected_findings\expected_findings.json",
    "templates\terraform\downsize_proposal.tf.j2",
    "templates\terraform\archive_proposal.tf.j2",
    "validate_inputs.py",
    "analyze_inputs.py",
    "generate_report.py",
    "generate_artifacts.py",
    "validate-terraform.ps1",
    "security-review.ps1"
)

$powerPointFiles = @($inventory | Where-Object Extension -eq ".pptx")
$contextFiles = @(
    $inventory |
        Where-Object { $_.RelativePath -match '(?i)(context|master).*\.(txt|md)$' }
)

$report = [System.Collections.Generic.List[string]]::new()
$report.Add("PROJECT FILE INVENTORY")
$report.Add("Project root: $root")
$report.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$report.Add("Total included files: $($inventory.Count)")
$report.Add("")
$report.Add("=== CATEGORY SUMMARY ===")

foreach ($row in $summary) {
    $report.Add(("{0,-22} Files: {1,4}  Size: {2,10} KB" -f $row.Category, $row.FileCount, $row.TotalSizeKB))
}

$report.Add("")
$report.Add("=== EXPECTED CORE FILES ===")

foreach ($item in $expectedFiles) {
    $status = if (Test-Path -LiteralPath (Join-Path $root $item)) { "FOUND" } else { "MISSING" }
    $report.Add("[$status] $item")
}

$report.Add("")
$report.Add("=== POWERPOINT FILES ===")

if ($powerPointFiles.Count -eq 0) {
    $report.Add("[NONE FOUND]")
} else {
    foreach ($item in $powerPointFiles) {
        $report.Add($item.RelativePath)
    }
}

$report.Add("")
$report.Add("=== MASTER AND CONTEXT FILES ===")

if ($contextFiles.Count -eq 0) {
    $report.Add("[NONE FOUND]")
} else {
    foreach ($item in $contextFiles) {
        $report.Add($item.RelativePath)
    }
}

$report.Add("")
$report.Add("=== COMPLETE INCLUDED FILE LIST ===")

foreach ($item in $inventory) {
    $report.Add("[$($item.Category)] $($item.RelativePath)")
}

$report | Set-Content -LiteralPath $TextReport -Encoding utf8
$inventory | Export-Csv -LiteralPath $CsvReport -NoTypeInformation -Encoding utf8

Write-Host "`nProject inventory completed." -ForegroundColor Green
Write-Host "Project root: $root"
Write-Host "Included files: $($inventory.Count)"
Write-Host "Text report: $TextReport"
Write-Host "CSV report: $CsvReport"

Write-Host "`nCategory summary:"
$summary | Format-Table -AutoSize

Write-Host "`nPowerPoint files found: $($powerPointFiles.Count)"
foreach ($item in $powerPointFiles) {
    Write-Host "  - $($item.RelativePath)"
}

Write-Host "`nMaster/context files found: $($contextFiles.Count)"
foreach ($item in $contextFiles) {
    Write-Host "  - $($item.RelativePath)"
}
