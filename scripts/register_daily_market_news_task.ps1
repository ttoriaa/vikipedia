param(
    [string]$TaskNameDryRun = "DailyMarketNewsDryRun",
    [string]$TaskNameRun = "DailyMarketNewsRun",
    [string]$DryRunTime = "08:30",
    [string]$RunTime = "08:45",
    [string]$RetryTime = "09:00",
    [string]$WorkspacePath = "c:\Users\Q653867\OneDrive - BMW Group\Desktop\V\vikipedia-agents",
    [string]$Markets = "us,cn,kr,hk",
    [int]$RequestTimeoutSec = 20
)

$runnerScriptPath = Join-Path $WorkspacePath "scripts\run_daily_market_news_task_runner.ps1"

if (-not (Test-Path $runnerScriptPath)) {
    throw "Runner script not found: $runnerScriptPath"
}

$commonArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runnerScriptPath`" -WorkspacePath `"$WorkspacePath`" -Markets `"$Markets`" -RequestTimeoutSec $RequestTimeoutSec"

$actionDryRun = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "$commonArgs -Mode dry-run" -WorkingDirectory $WorkspacePath
$actionRun = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "$commonArgs -Mode run" -WorkingDirectory $WorkspacePath

$triggerDryRunPrimary = New-ScheduledTaskTrigger -Daily -At $DryRunTime
$triggerDryRunRetry = New-ScheduledTaskTrigger -Daily -At $RetryTime
$triggerRunPrimary = New-ScheduledTaskTrigger -Daily -At $RunTime

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName $TaskNameDryRun -Action $actionDryRun -Trigger @($triggerDryRunPrimary, $triggerDryRunRetry) -Settings $settings -Force | Out-Null
Register-ScheduledTask -TaskName $TaskNameRun -Action $actionRun -Trigger $triggerRunPrimary -Settings $settings -Force | Out-Null

Write-Host "Scheduled task created/updated: $TaskNameDryRun at $DryRunTime (retry at $RetryTime)"
Write-Host "Scheduled task created/updated: $TaskNameRun at $RunTime"
Write-Host "Runner: $runnerScriptPath"
Write-Host "Markets: $Markets"
