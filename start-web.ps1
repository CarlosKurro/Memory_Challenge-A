param([int]$Port = 8765)

$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskUrl = 'http://127.0.0.1:' + $Port
$taskOutput = Join-Path $taskRoot 'output'
New-Item -ItemType Directory -Force -Path $taskOutput | Out-Null

try {
    $taskHealth = Invoke-RestMethod -Uri ($taskUrl + '/api/health') -TimeoutSec 2
    if ($taskHealth.app -eq 'challenge-a-memory-chat') {
        Write-Output ('Memory Chat is already running: ' + $taskUrl)
        exit 0
    }
} catch {
    # A new server is started when no Memory Chat server is available.
}

$taskPython = (Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$taskScript = Join-Path $taskRoot 'webapp.py'
$taskProcess = Start-Process -FilePath $taskPython `
    -ArgumentList @('-X', 'utf8', '-u', ('"' + $taskScript + '"'), '--port', [string]$Port) `
    -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $taskOutput 'web-server.log') `
    -RedirectStandardError (Join-Path $taskOutput 'web-server-error.log')
$taskProcess.Id | Set-Content -LiteralPath (Join-Path $taskOutput 'web-server.pid')

for ($taskAttempt = 0; $taskAttempt -lt 20; $taskAttempt++) {
    Start-Sleep -Milliseconds 250
    try {
        $taskHealth = Invoke-RestMethod -Uri ($taskUrl + '/api/health') -TimeoutSec 2
        if ($taskHealth.app -eq 'challenge-a-memory-chat') {
            Write-Output ('Memory Chat is running: ' + $taskUrl)
            Write-Output 'Open the URL in your browser. Data is saved in data/web-chat.sqlite3.'
            exit 0
        }
    } catch {
        if ($taskProcess.HasExited) { break }
    }
}
throw ('Server did not start. Check output/web-server-error.log; try another port with -Port 8766.')
