[CmdletBinding()]
param(
    [string]$ProjectRoot = "."
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$rootPath = (Resolve-Path -LiteralPath $ProjectRoot).Path

$excludedDirectoryNames = @(
    ".venv",
    ".checkov-venv",
    ".git",
    "output",
    "node_modules",
    "old versions",
    "tool-smoke-test"
)

$includedExtensions = @(
    ".py",
    ".ps1",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
    ".md",
    ".j2",
    ".tf"
)

$files = @(
    Get-ChildItem -LiteralPath $rootPath -Recurse -File |
        Where-Object {
            $file = $_
            $relativePath = $file.FullName.Substring(
                $rootPath.Length
            ).TrimStart([char[]]"\/")
            $pathParts = $relativePath -split "[\\/]"

            $isExcludedDirectory = $false

            foreach ($part in $pathParts) {
                if ($excludedDirectoryNames -contains $part) {
                    $isExcludedDirectory = $true
                    break
                }

                if ($part -like "session*-extracted") {
                    $isExcludedDirectory = $true
                    break
                }
            }

            $extensionIncluded = $includedExtensions -contains $file.Extension.ToLowerInvariant()
            $specialFileIncluded = $file.Name -in @(
                ".env.example",
                ".gitignore"
            )

            -not $isExcludedDirectory -and
            $file.Name -ne "security-review.ps1" -and
            $file.Name -ne "identify-secret-match.ps1" -and
            ($extensionIncluded -or $specialFileIncluded)
        }
)

$patterns = @(
    'AKIA[0-9A-Z]{16}',
    'BEGIN [A-Z ]*PRIVATE KEY',
    '(?i)client_secret\s*=',
    '(?i)access_key\s*=',
    '(?i)secret_key\s*=',
    '(?i)password\s*=',
    '(?i)token\s*='
)

$matches = @(
    $files |
        Select-String -Pattern $patterns -ErrorAction SilentlyContinue
)

$terraformFiles = @(
    $files |
        Where-Object { $_.Extension -eq ".tf" }
)

$unsafeTerraform = @(
    $terraformFiles |
        Select-String -Pattern @(
            'terraform\s+apply',
            'terraform\s+destroy'
        ) -ErrorAction SilentlyContinue
)

Write-Host "Files reviewed: $($files.Count)"
Write-Host "Potential secret-pattern matches: $($matches.Count)"
Write-Host "Unsafe source Terraform matches: $($unsafeTerraform.Count)"

if ($matches.Count -gt 0) {
    Write-Warning (
        "Review potential secret-pattern matches; " +
        "some may be safe placeholders or test strings."
    )

    foreach ($match in $matches) {
        $matchedText = ""

        if ($null -ne $match.Line) {
            $matchedText = $match.Line.Trim()
        }

        Write-Host "`nPotential match:" -ForegroundColor Yellow
        Write-Host "File: $($match.Path)"
        Write-Host "Line: $($match.LineNumber)"
        Write-Host "Text: $matchedText"
        Write-Host "Pattern: $($match.Pattern)"
    }
}

if ($unsafeTerraform.Count -gt 0) {
    Write-Warning "Unsafe Terraform command text was found in source .tf files."

    foreach ($match in $unsafeTerraform) {
        $matchedText = ""

        if ($null -ne $match.Line) {
            $matchedText = $match.Line.Trim()
        }

        Write-Host "`nUnsafe Terraform match:" -ForegroundColor Red
        Write-Host "File: $($match.Path)"
        Write-Host "Line: $($match.LineNumber)"
        Write-Host "Text: $matchedText"
        Write-Host "Pattern: $($match.Pattern)"
    }
}

$report = [PSCustomObject]@{
    FilesReviewed = $files.Count
    PotentialSecretMatches = $matches.Count
    UnsafeTerraformMatches = $unsafeTerraform.Count
    RequiresManualReview = (
        $matches.Count -gt 0 -or
        $unsafeTerraform.Count -gt 0
    )
}

Write-Host "`nSecurity review summary:"
$report | ConvertTo-Json | Write-Host

if ($unsafeTerraform.Count -gt 0) {
    exit 1
}

exit 0
