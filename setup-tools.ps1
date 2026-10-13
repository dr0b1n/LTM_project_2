$terraformPath = "C:\Users\T9925\Tools\Terraform"
$tflintPath = "C:\Users\T9925\Tools\TFLint"

if (Test-Path "$terraformPath\terraform.exe") {
    $env:Path = "$terraformPath;$env:Path"
    Write-Host "Terraform available: $terraformPath\terraform.exe"
} else {
    Write-Warning "Terraform was not found at $terraformPath"
}

if (Test-Path "$tflintPath\tflint.exe") {
    $env:Path = "$tflintPath;$env:Path"
    Write-Host "TFLint available: $tflintPath\tflint.exe"
} else {
    Write-Warning "TFLint was not found at $tflintPath"
}

terraform version
tflint --version