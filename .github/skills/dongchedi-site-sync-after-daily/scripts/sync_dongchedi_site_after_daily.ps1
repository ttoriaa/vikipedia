param(
    [string]$Date,
    [string]$Deploy = 'false',
    [string]$DispatchWorkflow = 'false'
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = $null
$candidate = Resolve-Path (Join-Path $scriptDir '..\..\..\..') -ErrorAction SilentlyContinue
if ($candidate -and (Test-Path (Join-Path $candidate.Path '.git'))) {
    $repoRoot = $candidate.Path
}

if (-not $repoRoot) {
    $walk = [System.IO.DirectoryInfo] (Resolve-Path $scriptDir)
    while ($walk -and -not (Test-Path (Join-Path $walk.FullName '.git'))) {
        $walk = $walk.Parent
    }
    if ($walk) {
        $repoRoot = $walk.FullName
    }
}

if (-not $repoRoot) {
    throw "Failed to locate repository root from script dir: $scriptDir"
}

$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
$reportRoot = Join-Path $repoRoot 'reports\dongchedi_daily'

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}

function Get-LatestReportDate {
    param([string]$RootPath)

    if (-not (Test-Path $RootPath)) {
        throw "Report root not found: $RootPath"
    }

    $dirs = Get-ChildItem -Path $RootPath -Directory |
        Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}$' } |
        Sort-Object Name

    if (-not $dirs) {
        throw "No daily report directories found under $RootPath"
    }

    return $dirs[-1].Name
}

function Assert-PathExists {
    param([string]$PathToCheck)

    if (-not (Test-Path $PathToCheck)) {
        throw "Required path missing: $PathToCheck"
    }
}

function Convert-ToBoolean {
    param(
        [string]$Value,
        [string]$ParameterName
    )

    $raw = if ($null -eq $Value) { '' } else { $Value }
    $normalized = $raw.Trim().ToLowerInvariant()
    switch ($normalized) {
        'true' { return $true }
        'false' { return $false }
        '1' { return $true }
        '0' { return $false }
        '' { return $false }
        default { throw "Invalid boolean value for ${ParameterName}: ${Value}" }
    }
}

$resolvedDate = if ($Date) { $Date } else { Get-LatestReportDate -RootPath $reportRoot }
$dailyDir = Join-Path $reportRoot $resolvedDate
$shouldDeploy = Convert-ToBoolean -Value $Deploy -ParameterName 'Deploy'
$shouldDispatchWorkflow = Convert-ToBoolean -Value $DispatchWorkflow -ParameterName 'DispatchWorkflow'

Assert-PathExists $dailyDir
Assert-PathExists (Join-Path $dailyDir 'filtered.csv')
Assert-PathExists (Join-Path $dailyDir 'summary.md')

Write-Host "Resolved date: $resolvedDate"

Push-Location $repoRoot
try {
    & $pythonExe '.\.github\skills\dongchedi-site-sync-after-daily\scripts\build_charging_visualizations.py' '--date' $resolvedDate
    if ($LASTEXITCODE -ne 0) {
        throw "Visualization build failed with exit code $LASTEXITCODE"
    }

    & $pythonExe '.\.github\skills\dongchedi-site-sync-after-daily\scripts\build_dongchedi_pages_site.py'
    if ($LASTEXITCODE -ne 0) {
        throw "Site assembly failed with exit code $LASTEXITCODE"
    }

    Copy-Item '.\index.html' '.\site\index.html' -Force

    $requiredOutputs = @(
        '.\site\data.html',
        '.\site\dashboard.html',
        '.\site\insights.html',
        ".\site\reports\$resolvedDate\charging_visualization_dashboard.html",
        '.\site\latest\charging_visualization_dashboard.html'
    )

    foreach ($path in $requiredOutputs) {
        Assert-PathExists $path
    }

    Write-Host 'Site files check: pass'

    if ($shouldDeploy) {
        $siteTargets = @(
            'site/data.html',
            'site/dashboard.html',
            'site/insights.html',
            'site/index.html',
            'site/latest/charging_visualization_dashboard.html',
            "site/reports/$resolvedDate"
        )

        git add -- $siteTargets
        $hasStaged = (git diff --cached --name-only).Trim()
        if ($hasStaged) {
            git commit -m "chore: sync dongchedi site for $resolvedDate"
            git push origin main
            Write-Host 'Deploy status: success'
        } else {
            Write-Host 'Deploy status: skipped (no staged changes)'
        }
    } else {
        Write-Host 'Deploy status: skipped'
    }

    if ($shouldDispatchWorkflow) {
        $gh = Get-Command gh -ErrorAction SilentlyContinue
        if (-not $gh) {
            throw 'gh CLI not found; cannot dispatch workflow automatically'
        }
        & $gh.Source 'workflow' 'run' '.github/workflows/dongchedi-pages.yml'
        if ($LASTEXITCODE -ne 0) {
            throw "Workflow dispatch failed with exit code $LASTEXITCODE"
        }
        Write-Host 'Workflow dispatch status: success'
    } else {
        Write-Host 'Workflow dispatch status: skipped'
    }
}
finally {
    Pop-Location
}
