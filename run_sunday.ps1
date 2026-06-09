# run_sunday.ps1 - COURSE MASTER Sun auto-run
$BASE   = "C:\Users\shiny\Dropbox\shinya_wa\coursemaster"
$CLAUDE = "C:\Users\shiny\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"
$date    = Get-Date -Format "yyyyMMdd"
$logFile = "$BASE\logs\sunday_$date.log"
$mainLog = "$BASE\logs\scheduler.log"

function Write-MainLog($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$ts] $msg" | Out-File -Append -Encoding UTF8 $mainLog
}

function Send-Toast {
    param([string]$Title, [string]$Body)
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $titleEsc = [System.Security.SecurityElement]::Escape($Title)
        $bodyEsc  = [System.Security.SecurityElement]::Escape($Body)
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>$titleEsc</text><text>$bodyEsc</text></binding></visual></toast>")
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("COURSE MASTER")
        $notifier.Show([Windows.UI.Notifications.ToastNotification]::new($xml))
        Write-MainLog "Toast sent: $Title"
    } catch {
        Write-MainLog "Toast failed: $_"
    }
}

Write-MainLog "Sunday job STARTED"
"=== COURSE MASTER Sunday $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -Encoding UTF8 $logFile

$promptFile  = "$BASE\prompt_sunday.txt"
$promptBase  = Get-Content -Encoding UTF8 $promptFile -Raw
$todayISO    = Get-Date -Format "yyyy-MM-dd"
$prompt      = "【実行日: $todayISO (日曜)】grade_race_predictor.py を実行する際は必ず --today フラグを付けること。レースJSON には race_date フィールド（YYYY-MM-DD 形式）を含めること。`n`n" + $promptBase

$htmlFile = "$BASE\output\prediction_$date.html"

try {
    Set-Location $BASE
    [System.Environment]::SetEnvironmentVariable("PYTHONIOENCODING", "utf-8")
    $result = & $CLAUDE -p --dangerously-skip-permissions $prompt 2>&1
    $exitCode = $LASTEXITCODE
    $result | Out-File -Append -Encoding UTF8 $logFile
    Write-MainLog "Sunday job COMPLETED (exit: $exitCode)"

    # 失敗条件チェック
    $reasons = @()
    if ($exitCode -ne 0) {
        $reasons += "異常終了 (exit $exitCode)"
    }
    if (-not (Test-Path $htmlFile)) {
        $reasons += "HTML未生成"
    }
    if (Select-String -Path $logFile -Pattern "ERROR" -Quiet) {
        $reasons += "ERRORログ検出"
    }

    if ($reasons.Count -gt 0) {
        $body = ($reasons -join " / ") + "`nログ: $logFile"
        Send-Toast "COURSE MASTER 予測失敗" $body
        Write-MainLog "FAILED: $($reasons -join ', ')"
    } else {
        Send-Toast "COURSE MASTER 予測完了" "HTMLレポート: $htmlFile"
        Start-Process $htmlFile
        Write-MainLog "HTML report opened: prediction_$date.html"

        # latest.html へコピー + latest_data.json 生成
        $latestHtml = "$BASE\output\latest.html"
        Copy-Item $htmlFile $latestHtml -Force
        Write-MainLog "Copied to latest.html"

        $pyOut = & python "$BASE\make_latest.py" 2>&1
        $pyOut | Out-File -Append -Encoding UTF8 $logFile
        Write-MainLog "make_latest.py: $pyOut"

        # GitHub push（予測のみ）※ レース後の照合・actual_result 更新は result_checker.py が push
        Set-Location $BASE
        git add "output\latest.html" "output\latest_data.json"
        $commitMsg = "prediction: $todayISO 予測更新（日）"
        git commit -m $commitMsg
        git push origin main
        Write-MainLog "GitHub push completed"
    }
} catch {
    $errMsg = "$_"
    Write-MainLog "Sunday job ERROR: $errMsg"
    "ERROR: $errMsg" | Out-File -Append -Encoding UTF8 $logFile
    Send-Toast "COURSE MASTER 予測失敗" "例外発生: $errMsg`nログ: $logFile"
}
