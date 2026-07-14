#Requires -Version 5.1
<#
.SYNOPSIS
  Register (or update) the Windows scheduled task that keeps the coupon-reminder
  Telegram bot running under pythonw, resilient to crashes, kills and reboots.

.DESCRIPTION
  Idempotent: re-running updates the task in place. Two triggers:
    * At logon                    -> starts the bot as soon as the user logs in.
    * Every 5 min (time trigger,  -> watchdog that keeps it alive.
      repeats for ~10 years)
  Combined with MultipleInstances=IgnoreNew, the watchdog is a no-op while the
  bot is alive and relaunches it within 5 minutes if it has died -- and never
  spawns a duplicate. RestartCount is a secondary safety net.

  Logs are written to logs\bot.log by run_service.py (pythonw has no console).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1
#>
param(
    [string]$TaskName = 'CouponReminderBot',
    [string]$Pythonw
)
$ErrorActionPreference = 'Stop'

$root   = Split-Path -Parent $PSScriptRoot
$script = Join-Path $root 'run_service.py'
if (-not (Test-Path $script)) { throw "Launcher not found: $script" }

if (-not $Pythonw) {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        $Pythonw = $cmd.Source
    } else {
        $py = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($py) {
            $cand = Join-Path (Split-Path $py.Source) 'pythonw.exe'
            if (Test-Path $cand) { $Pythonw = $cand }
        }
    }
}
if (-not $Pythonw -or -not (Test-Path $Pythonw)) {
    throw "Could not locate pythonw.exe. Re-run with -Pythonw '<full path to pythonw.exe>'."
}

$me = [Security.Principal.WindowsIdentity]::GetCurrent().Name

$action = New-ScheduledTaskAction -Execute $Pythonw -Argument "`"$script`"" -WorkingDirectory $root

# Trigger 1: start immediately at logon.
$logon = New-ScheduledTaskTrigger -AtLogOn -User $me

# Trigger 2: 5-minute watchdog. Fires on the wall clock regardless of login
# state; IgnoreNew makes it harmless while the bot runs and a restart when not.
$watch = New-ScheduledTaskTrigger -Once -At (Get-Date).Date `
            -RepetitionInterval (New-TimeSpan -Minutes 5) `
            -RepetitionDuration  (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
                -MultipleInstances IgnoreNew `
                -AllowStartIfOnBatteries `
                -DontStopIfGoingOnBatteries `
                -StartWhenAvailable `
                -RestartCount 99 `
                -RestartInterval (New-TimeSpan -Minutes 1) `
                -ExecutionTimeLimit ([TimeSpan]::Zero)   # PT0S = no time limit

$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($logon, $watch) `
    -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "OK: registered/updated scheduled task '$TaskName'"
Write-Host "  pythonw     : $Pythonw"
Write-Host "  launcher    : $script"
Write-Host "  working dir : $root"
Write-Host ""
Write-Host "Start it now:   Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Check status:   Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
