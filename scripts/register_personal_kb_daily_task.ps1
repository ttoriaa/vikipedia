param(
    [string]$TaskName = "PersonalKnowledgeBaseDailyRefresh",
    [string]$RunTime = "21:30",
    [string]$RetryTime = "22:00",
    [string]$WorkspacePath = "c:\Users\Q653867\OneDrive - BMW Group\Desktop\V\vikipedia-agents",
    [int]$TopSkills = 12,
    [int]$RecentLimit = 15
)

$runnerScriptPath = Join-Path $WorkspacePath "scripts\run_personal_kb_task_runner.ps1"

if (-not (Test-Path $runnerScriptPath)) {
    throw "Runner script not found: $runnerScriptPath"
}

$commonArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runnerScriptPath`" -WorkspacePath `"$WorkspacePath`" -TopSkills $TopSkills -RecentLimit $RecentLimit"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "$commonArgs -Mode run" -WorkingDirectory $WorkspacePath
$triggerPrimary = New-ScheduledTaskTrigger -Daily -At $RunTime
$triggerRetry = New-ScheduledTaskTrigger -Daily -At $RetryTime

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($triggerPrimary, $triggerRetry) -Settings $settings -Force | Out-Null

Write-Host "Scheduled task created/updated: $TaskName at $RunTime (retry at $RetryTime)"
Write-Host "Runner: $runnerScriptPath"
Write-Host "TopSkills: $TopSkills | RecentLimit: $RecentLimit"
