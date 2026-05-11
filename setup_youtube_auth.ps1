# YouTube OAuth Token Generator
# Run this once to generate your YOUTUBE_REFRESH_TOKEN

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "YouTube OAuth Token Generator" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Find client_secrets.json
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$secretsPath = Join-Path $scriptDir "client_secrets.json"

if (-not (Test-Path $secretsPath)) {
    Write-Host "client_secrets.json not found in: $scriptDir" -ForegroundColor Yellow
    $secretsPath = Read-Host "Enter full path to your client_secrets.json"
    if (-not (Test-Path $secretsPath)) {
        Write-Host "File not found. Exiting." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Found credentials file." -ForegroundColor Green

# Step 2: Parse credentials
$secretsRaw = Get-Content $secretsPath -Raw
$secrets = $secretsRaw | ConvertFrom-Json

$creds = $null
if ($secrets.PSObject.Properties.Name -contains "installed") {
    $creds = $secrets.installed
} elseif ($secrets.PSObject.Properties.Name -contains "web") {
    $creds = $secrets.web
} else {
    Write-Host "ERROR: Cannot read client_secrets.json format." -ForegroundColor Red
    exit 1
}

$clientId     = $creds.client_id
$clientSecret = $creds.client_secret
Write-Host "Client ID loaded." -ForegroundColor Green
Write-Host ""

# Step 3: Start local HTTP listener on fixed port 9090
$port = 9090
$redirectUri = "http://localhost:$port"

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$port/")
try {
    $listener.Start()
    Write-Host "Local server started on port $port." -ForegroundColor Green
} catch {
    Write-Host "ERROR: Port $port is busy. Please close other apps and retry." -ForegroundColor Red
    exit 1
}

# Step 4: Build OAuth URL and open browser
$scope   = "https://www.googleapis.com/auth/youtube.upload"
$authUrl = "https://accounts.google.com/o/oauth2/v2/auth" +
           "?client_id=" + [Uri]::EscapeDataString($clientId) +
           "&redirect_uri=" + [Uri]::EscapeDataString($redirectUri) +
           "&response_type=code" +
           "&scope=" + [Uri]::EscapeDataString($scope) +
           "&access_type=offline" +
           "&prompt=consent"

Write-Host ""
Write-Host "Opening browser..." -ForegroundColor Cyan
Write-Host "Sign in as: likithshetty32@gmail.com and click Allow." -ForegroundColor Yellow
Write-Host ""

Start-Process $authUrl
Write-Host "Waiting for Google to redirect back (do not close this window)..." -ForegroundColor Cyan

# Step 5: Wait for redirect and capture auth code
$context  = $listener.GetContext()
$rawQuery = $context.Request.Url.Query.TrimStart("?")

$authCode = $null
$errMsg   = $null

foreach ($param in $rawQuery.Split("&")) {
    $kv = $param.Split("=", 2)
    if ($kv.Count -eq 2) {
        if ($kv[0] -eq "code")  { $authCode = [Uri]::UnescapeDataString($kv[1]) }
        if ($kv[0] -eq "error") { $errMsg   = [Uri]::UnescapeDataString($kv[1]) }
    }
}

# Send response to browser
if ($authCode) {
    $html = "<html><body style='font-family:sans-serif;text-align:center;padding:60px;background:#111;color:white'><h1 style='color:#8a2be2'>Authorization Successful!</h1><p>You can close this tab and return to PowerShell.</p></body></html>"
} else {
    $html = "<html><body style='font-family:sans-serif;text-align:center;padding:60px;background:#111;color:white'><h1 style='color:red'>Authorization Failed</h1><p>$errMsg</p></body></html>"
}

$buffer = [System.Text.Encoding]::UTF8.GetBytes($html)
$context.Response.ContentLength64 = $buffer.Length
$context.Response.OutputStream.Write($buffer, 0, $buffer.Length)
$context.Response.Close()
$listener.Stop()

if ($errMsg) {
    Write-Host "ERROR: Google returned: $errMsg" -ForegroundColor Red
    exit 1
}

if (-not $authCode) {
    Write-Host "ERROR: No authorization code received." -ForegroundColor Red
    exit 1
}

Write-Host "Authorization code received!" -ForegroundColor Green

# Step 6: Exchange auth code for tokens
Write-Host "Exchanging code for tokens..." -ForegroundColor Cyan

$body = "client_id=" + [Uri]::EscapeDataString($clientId) +
        "&client_secret=" + [Uri]::EscapeDataString($clientSecret) +
        "&code=" + [Uri]::EscapeDataString($authCode) +
        "&redirect_uri=" + [Uri]::EscapeDataString($redirectUri) +
        "&grant_type=authorization_code"

$tokenResponse = Invoke-RestMethod -Uri "https://oauth2.googleapis.com/token" -Method Post -Body $body -ContentType "application/x-www-form-urlencoded"

if (-not $tokenResponse.refresh_token) {
    Write-Host "ERROR: No refresh_token in response." -ForegroundColor Red
    Write-Host "Make sure you clicked Publish App on the OAuth consent screen." -ForegroundColor Yellow
    $tokenResponse | ConvertTo-Json
    exit 1
}

$refreshToken = $tokenResponse.refresh_token

# Step 7: Display result
Write-Host ""
Write-Host "==============================" -ForegroundColor Green
Write-Host "SUCCESS!" -ForegroundColor Green
Write-Host "==============================" -ForegroundColor Green
Write-Host ""
Write-Host "GitHub Secret Name  : YOUTUBE_REFRESH_TOKEN" -ForegroundColor Yellow
Write-Host "GitHub Secret Value : $refreshToken" -ForegroundColor White
Write-Host ""

# Step 8: Copy to clipboard
$refreshToken | Set-Clipboard
Write-Host "Copied to clipboard!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Now go to:" -ForegroundColor White
Write-Host "https://github.com/Likithshetty24/fantasyverse-bot/settings/secrets/actions" -ForegroundColor Cyan
Write-Host "Update YOUTUBE_REFRESH_TOKEN and paste from clipboard." -ForegroundColor White
Write-Host ""
