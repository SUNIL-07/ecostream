$envLines = Get-Content "c:\EcoStream\.env" | Where-Object { $_ -match "=" }
$keys = @{}
foreach ($line in $envLines) {
    if ($line.Trim() -notmatch "^#") {
        $parts = $line.Split("=", 2)
        $keys[$parts[0].Trim()] = $parts[1].Trim().Trim('"')
    }
}

$waqiKey = $keys["WAQI_API_KEY"]
$owmKey = $keys["OWM_API_KEY"]

Write-Host "--- WAQI API ---"
$waqiUrl = "https://api.waqi.info/feed/New`%20Delhi/?token=$waqiKey"
try {
    $waqiRes = Invoke-RestMethod -Uri $waqiUrl
    $waqiRes.data | ConvertTo-Json -Depth 10
} catch {
    Write-Host "WAQI Error: $_"
}

Write-Host "--- OWM API ---"
$owmUrl = "https://api.openweathermap.org/data/2.5/weather?q=New`%20Delhi,IN&appid=$owmKey&units=metric"
try {
    $owmRes = Invoke-RestMethod -Uri $owmUrl
    $owmRes | ConvertTo-Json -Depth 10
} catch {
    Write-Host "OWM Error: $_"
}
