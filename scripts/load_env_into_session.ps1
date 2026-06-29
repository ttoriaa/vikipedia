param(
    [string]$EnvFile = ".env",
    [switch]$Override,
    [switch]$ShowKeys
)

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envPath = Join-Path $root $EnvFile

if (-not (Test-Path $envPath)) {
    Write-Error "Env file not found: $envPath"
    exit 1
}

$loaded = New-Object System.Collections.Generic.List[string]
$skipped = New-Object System.Collections.Generic.List[string]

Get-Content $envPath -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()

    if ([string]::IsNullOrWhiteSpace($line)) { return }
    if ($line.StartsWith("#")) { return }

    if ($line.StartsWith("export ")) {
        $line = $line.Substring(7).Trim()
    }

    $eq = $line.IndexOf("=")
    if ($eq -le 0) { return }

    $key = $line.Substring(0, $eq).Trim()
    $value = $line.Substring($eq + 1)

    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    $existing = [Environment]::GetEnvironmentVariable($key, "Process")
    if (-not $Override -and -not [string]::IsNullOrEmpty($existing)) {
        $skipped.Add($key) | Out-Null
        return
    }

    [Environment]::SetEnvironmentVariable($key, $value, "Process")
    $loaded.Add($key) | Out-Null
}

Write-Output "Loaded $($loaded.Count) keys from $envPath into current PowerShell process."
if ($skipped.Count -gt 0) {
    Write-Output "Skipped $($skipped.Count) existing keys (use -Override to replace)."
}

if ($ShowKeys) {
    Write-Output "Loaded keys:"
    $loaded | Sort-Object | ForEach-Object { Write-Output "- $_" }
}
