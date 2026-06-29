param(
    [string]$WorkspacePath = "c:\Users\Q653867\OneDrive - BMW Group\Desktop\V\vikipedia-agents",
    [ValidateSet("dry-run", "run")]
    [string]$Mode = "run",
    [int]$TopSkills = 12,
    [int]$RecentLimit = 15,
    [int]$TaskTimeoutSec = 600
)

$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false

Set-Location $WorkspacePath

$pythonPath = Join-Path $WorkspacePath ".venv\Scripts\python.exe"
$scriptPath = Join-Path $WorkspacePath "scripts\build_personal_knowledge_base.py"

if (-not (Test-Path $pythonPath)) {
    throw "Python not found: $pythonPath"
}

if (-not (Test-Path $scriptPath)) {
    throw "Script not found: $scriptPath"
}

$logDir = Join-Path $WorkspacePath "reports\task_logs"
if (-not (Test-Path $logDir)) {
    New-Item -Path $logDir -ItemType Directory -Force | Out-Null
}

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$logPath = Join-Path $logDir ("personal_kb_task_{0}.log" -f $stamp)
$lockPath = Join-Path $logDir "personal_kb_task.lock"
$outTmp = Join-Path $logDir ("personal_kb_task_stdout_{0}.tmp" -f ([guid]::NewGuid().ToString("N")))
$errTmp = Join-Path $logDir ("personal_kb_task_stderr_{0}.tmp" -f ([guid]::NewGuid().ToString("N")))

function Append-TempOutput {
    param(
        [string]$StdoutPath,
        [string]$StderrPath,
        [string]$TargetLogPath
    )
    if (Test-Path $StdoutPath) {
        Get-Content $StdoutPath | Out-File -FilePath $TargetLogPath -Encoding UTF8 -Append
        Remove-Item $StdoutPath -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $StderrPath) {
        Get-Content $StderrPath | Out-File -FilePath $TargetLogPath -Encoding UTF8 -Append
        Remove-Item $StderrPath -Force -ErrorAction SilentlyContinue
    }
}

try {
    $lockStream = New-Object System.IO.FileStream($lockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
}
catch {
    "[$(Get-Date -Format s)] SKIP personal kb task because another instance is running" | Out-File -FilePath $logPath -Encoding UTF8 -Append
    exit 0
}

"[$(Get-Date -Format s)] START personal kb task mode=$Mode top_skills=$TopSkills recent_limit=$RecentLimit" | Out-File -FilePath $logPath -Encoding UTF8 -Append

try {
    $today = Get-Date -Format "yyyy-MM-dd"
    $effectiveTopSkills = if ($Mode -eq "dry-run") { [Math]::Min($TopSkills, 8) } else { $TopSkills }
    $effectiveRecentLimit = if ($Mode -eq "dry-run") { [Math]::Min($RecentLimit, 8) } else { $RecentLimit }

    $argList = @(
        ('"{0}"' -f $scriptPath),
        "--date", $today,
        "--top-skills", [string]$effectiveTopSkills,
        "--recent-limit", [string]$effectiveRecentLimit
    )

    $proc = Start-Process -FilePath $pythonPath -ArgumentList ($argList -join " ") -PassThru -NoNewWindow -RedirectStandardOutput $outTmp -RedirectStandardError $errTmp
    $finished = $proc.WaitForExit($TaskTimeoutSec * 1000)

    if (-not $finished) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Append-TempOutput -StdoutPath $outTmp -StderrPath $errTmp -TargetLogPath $logPath
        "[$(Get-Date -Format s)] FAIL personal kb task timeout after ${TaskTimeoutSec}s" | Out-File -FilePath $logPath -Encoding UTF8 -Append
        exit 124
    }

    Append-TempOutput -StdoutPath $outTmp -StderrPath $errTmp -TargetLogPath $logPath
    $exitCode = [int]$proc.ExitCode
    if ($exitCode -ne 0) {
        "[$(Get-Date -Format s)] FAIL personal kb task exit=$exitCode" | Out-File -FilePath $logPath -Encoding UTF8 -Append
        exit $exitCode
    }

    "[$(Get-Date -Format s)] DONE personal kb task" | Out-File -FilePath $logPath -Encoding UTF8 -Append
    exit 0
}
finally {
    if (Test-Path $outTmp) {
        Remove-Item $outTmp -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $errTmp) {
        Remove-Item $errTmp -Force -ErrorAction SilentlyContinue
    }
    if ($lockStream) {
        $lockStream.Close()
        $lockStream.Dispose()
    }
    if (Test-Path $lockPath) {
        Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
    }
}
