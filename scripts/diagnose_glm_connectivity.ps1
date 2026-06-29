param(
    [string]$EnvFile = ".env",
    [string]$TestModel = "glm-4-flash",
    [int]$TimeoutSec = 20
)

$ErrorActionPreference = "Stop"

function Set-EnvFromFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if ([string]::IsNullOrWhiteSpace($line)) { return }
        if ($line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }

        $name = $line.Substring(0, $eq).Trim()
        $value = $line.Substring($eq + 1).Trim().Trim('"').Trim("'")
        if (-not [string]::IsNullOrWhiteSpace($name)) {
            Set-Item -Path ("Env:" + $name) -Value $value
        }
    }
}

function Show-ProxyStatus {
    $proxyVars = @("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy")
    foreach ($n in $proxyVars) {
        $v = [Environment]::GetEnvironmentVariable($n)
        if ([string]::IsNullOrWhiteSpace($v)) {
            Write-Output ("PROXY_{0}=EMPTY" -f $n)
        }
        else {
            Write-Output ("PROXY_{0}=SET" -f $n)
        }
    }
}

Set-EnvFromFile -Path $EnvFile

$apiKey = [Environment]::GetEnvironmentVariable("OPENAI_API_KEY")
$baseUrl = [Environment]::GetEnvironmentVariable("OPENAI_BASE_URL")
if ([string]::IsNullOrWhiteSpace($baseUrl)) {
    $baseUrl = "https://api.openai.com/v1"
}
$baseUrl = $baseUrl.TrimEnd("/")

Write-Output ("DIAG_ENV_FILE={0}" -f $EnvFile)
Write-Output ("DIAG_OPENAI_BASE_URL={0}" -f $baseUrl)
Write-Output ("DIAG_OPENAI_API_KEY_SET={0}" -f (-not [string]::IsNullOrWhiteSpace($apiKey)))

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Output "DIAG_RESULT=FAIL"
    Write-Output "DIAG_REASON=OPENAI_API_KEY missing"
    exit 1
}

Show-ProxyStatus

$hostName = [Uri]$baseUrl
try {
    $dns = Resolve-DnsName -Name $hostName.Host -Type A -ErrorAction Stop
    if ($dns) {
        Write-Output ("DIAG_DNS={0}:OK" -f $hostName.Host)
    }
}
catch {
    Write-Output ("DIAG_DNS={0}:FAILED" -f $hostName.Host)
}

$chatUri = $baseUrl + "/chat/completions"
$headers = @{
    Authorization = "Bearer $apiKey"
    "Content-Type" = "application/json"
}

$payload = @{
    model = $TestModel
    temperature = 0
    messages = @(
        @{
            role = "user"
            content = "Reply exactly: OK_GLM"
        }
    )
} | ConvertTo-Json -Depth 8

try {
    $resp = Invoke-RestMethod -Method Post -Uri $chatUri -Headers $headers -Body $payload -TimeoutSec $TimeoutSec
    $txt = $resp.choices[0].message.content
    Write-Output "DIAG_CHAT_HTTP=200"
    if ([string]::IsNullOrWhiteSpace($txt)) {
        Write-Output "DIAG_CHAT_STATUS=EMPTY_REPLY"
        Write-Output "DIAG_RESULT=FAIL"
        exit 2
    }

    Write-Output "DIAG_CHAT_STATUS=OK"
    Write-Output ("DIAG_CHAT_REPLY={0}" -f $txt)
    Write-Output "DIAG_RESULT=PASS"
    exit 0
}
catch {
    $code = "NA"
    $msg = $_.Exception.Message
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
        $code = [int]$_.Exception.Response.StatusCode
    }
    Write-Output ("DIAG_CHAT_HTTP={0}" -f $code)
    Write-Output ("DIAG_CHAT_STATUS=FAILED")
    Write-Output ("DIAG_CHAT_ERROR={0}" -f $msg)
    Write-Output "DIAG_RESULT=FAIL"
    exit 3
}
