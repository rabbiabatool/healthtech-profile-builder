# Evidence capture helper for Week 2 verification
# Usage: .\scripts\capture_evidence.ps1 -Name "test-name" -Command "pytest -v" -WorkDir "backend"
param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$Command,
    [string]$WorkDir = "backend"
)

$root = "c:\Users\Super\Documents\healthtech-profile-builder"
$evidenceDir = "$root\docs\evidence\week2"
$outFile = "$evidenceDir\$Name.txt"

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss K"
$fullWorkDir = "$root\$WorkDir"

# Header
$header = @"
=== Evidence: $Name ===
Timestamp : $timestamp
Command   : $Command
WorkDir   : $fullWorkDir
---
"@

Set-Location $fullWorkDir

try {
    $output = Invoke-Expression "$Command 2>&1" | Out-String
    $exitCode = $LASTEXITCODE
    if ($null -eq $exitCode) { $exitCode = 0 }
} catch {
    $output = $_.Exception.Message
    $exitCode = 1
}

$footer = @"

---
Exit code : $exitCode
Status    : $(if ($exitCode -eq 0) { "PASS" } else { "FAIL" })
"@

($header + $output + $footer) | Out-File -FilePath $outFile -Encoding utf8
Write-Output "Saved: $outFile (exit=$exitCode)"

