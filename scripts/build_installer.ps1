<#
.SYNOPSIS
    Build FilePilot AI Windows Installer
.DESCRIPTION
    Full build pipeline:
    1. Install Python deps
    2. PyInstaller build
    3. Detect / download Inno Setup
    4. Compile installer
    5. (Optional) Digital sign the installer
    6. Generate SHA256 checksum
    Works both locally and in GitHub Actions CI.

.PARAMETER SkipPyInstaller
    Skip the PyInstaller step (reuse existing dist/FilePilot/ folder).
    Useful for iterating on the installer script.

.PARAMETER SkipSigning
    Skip code signing even if a certificate is available.

.EXAMPLE
    .\scripts\build_installer.ps1                    # Full build
    .\scripts\build_installer.ps1 -SkipPyInstaller   # Rebuild installer only
    .\scripts\build_installer.ps1 -SkipSigning       # Build without signing
#>

param(
    [switch]$SkipPyInstaller,
    [switch]$SkipSigning
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $ProjectRoot

# ── Read version from project ──
$versionLine = Select-String -Path "filepilot\__init__.py" -Pattern '__version__\s*=\s*"([^"]+)"'
if ($versionLine) {
    $AppVersion = $versionLine.Matches.Groups[1].Value
} else {
    $AppVersion = "0.0.0"
    Write-Host "  ⚠ Could not detect version from __init__.py, using 0.0.0" -ForegroundColor Yellow
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
Write-Host "=== FilePilot AI v$AppVersion — Windows Installer Build ===" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Install dependencies ──
Write-Host "[1/4] Installing Python dependencies..." -ForegroundColor Yellow
$pipResult = pip install -e . 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ pip install failed:" -ForegroundColor Red
    Write-Host $pipResult
    throw "pip install failed"
}
$pipResult = pip install pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ pyinstaller install failed:" -ForegroundColor Red
    Write-Host $pipResult
    throw "pyinstaller install failed"
}
Write-Host "  ✅ Dependencies ready" -ForegroundColor Green

# ── Step 2: PyInstaller build ──
if (-not $SkipPyInstaller) {
    Write-Host "[2/4] Building with PyInstaller..." -ForegroundColor Yellow

    # Prerequisite check
    if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
        Write-Host "  ❌ pyinstaller not found. Install with: pip install pyinstaller" -ForegroundColor Red
        exit 1
    }

    # Clean previous builds
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
    if (Test-Path "dist\FilePilot") { Remove-Item -Recurse -Force "dist\FilePilot" }

    pyinstaller FilePilot.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

    $exePath = "dist\FilePilot\FilePilot.exe"
    if (-not (Test-Path $exePath)) { throw "Build artifact not found: $exePath" }

    $size = [math]::Round((Get-Item $exePath).Length / 1MB, 2)
    Write-Host "  ✅ PyInstaller OK — FilePilot.exe ($size MB)" -ForegroundColor Green
} else {
    Write-Host "[2/4] PyInstaller build skipped (--SkipPyInstaller)" -ForegroundColor Yellow
    $exePath = "dist\FilePilot\FilePilot.exe"
    if (-not (Test-Path $exePath)) {
        throw "SkipPyInstaller specified but dist\FilePilot\FilePilot.exe not found. Run full build first."
    }
    $size = [math]::Round((Get-Item $exePath).Length / 1MB, 2)
    Write-Host "  📦 Using existing FilePilot.exe ($size MB)" -ForegroundColor Cyan
}

# ── Step 3: Find Inno Setup ──
Write-Host "[3/4] Checking Inno Setup..." -ForegroundColor Yellow

function Find-ISCC {
    # Check PATH first
    $pathIscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($pathIscc) { return $pathIscc.Source }

    # Check env var
    if ($env:ISCC_PATH -and (Test-Path $env:ISCC_PATH)) { return $env:ISCC_PATH }

    # Common install locations
    $paths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 5\ISCC.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }

    # Check Chocolatey
    $chocoPath = "$env:ProgramData\chocolatey\lib\innosetup\tools\ISCC.exe"
    if (Test-Path $chocoPath) { return $chocoPath }

    # Check Scoop
    $scoopPath = "$env:USERPROFILE\scoop\apps\innosetup\current\ISCC.exe"
    if (Test-Path $scoopPath) { return $scoopPath }

    return $null
}

$isccPath = Find-ISCC

if (-not $isccPath) {
    Write-Host "  ⚠ Inno Setup not found locally." -ForegroundColor Yellow
    Write-Host "  ℹ Install with: winget install JRSoftware.InnoSetup" -ForegroundColor Cyan
    Write-Host "  ℹ Or: choco install innosetup" -ForegroundColor Cyan
    Write-Host "  ℹ Or manually: https://jrsoftware.org/isdl.php" -ForegroundColor Cyan

    # Download in CI
    if ($env:CI -or $env:GITHUB_ACTIONS) {
        Write-Host "  → CI detected, downloading Inno Setup..." -ForegroundColor Yellow
        $innoUrl = "https://jrsoftware.org/download.php/innosetup.exe"
        $innoInstaller = "$env:TEMP\innosetup.exe"
        $innoDir = "$env:TEMP\InnoSetup"

        try {
            Invoke-WebRequest -Uri $innoUrl -OutFile $innoInstaller -UseBasicParsing -MaximumRedirection 10
            Start-Process -FilePath $innoInstaller -ArgumentList "/VERYSILENT /DIR=$innoDir /NORESTART /SUPPRESSMSGBOXES" -Wait
            $isccPath = "$innoDir\ISCC.exe"
            if (-not (Test-Path $isccPath)) { throw "Inno Setup install failed: ISCC.exe not found at $innoDir" }
            Write-Host "  ✅ Inno Setup downloaded to $innoDir" -ForegroundColor Green
        } catch {
            Write-Host "  ❌ Failed to download Inno Setup: $_" -ForegroundColor Red
            Write-Host "  → Falling back: binaries ready at dist\FilePilot\" -ForegroundColor Magenta
            return
        }
    } else {
        Write-Host "  → Skipping installer compilation." -ForegroundColor Magenta
        Write-Host "  📁 Binaries ready at: dist\FilePilot\" -ForegroundColor Cyan
        return
    }
} else {
    Write-Host "  ✅ Found Inno Setup: $isccPath" -ForegroundColor Green
}

# ── Step 4: Compile installer (pass version to ISS) ──
Write-Host "[4/4] Compiling installer with Inno Setup..." -ForegroundColor Yellow

$issFile = "scripts\filepilot-installer.iss"
if (-not (Test-Path $issFile)) { throw "Installer script not found: $issFile" }

# CRITICAL: pass the detected version to Inno Setup via /d flag
& $isccPath "/dMyAppVersion=$AppVersion" $issFile
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed" }

# ── Step 5: Digital signing (optional) ──
$signTool = $env:SIGNTOOL_PATH
$certHash = $env:SIGN_CERTIFICATE_SHA1
$timestampServer = $env:SIGN_TIMESTAMP_SERVER

if (-not $SkipSigning -and $signTool -and $certHash) {
    Write-Host "[5/5] Signing installer..." -ForegroundColor Yellow

    if (-not $timestampServer) {
        $timestampServer = "http://timestamp.digicert.com"
    }

    $installer = Get-ChildItem "dist\FilePilot-AI-Setup-*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $installer) { throw "Installer not found for signing" }

    $signArgs = @(
        "sign",
        "/fd", "SHA256",
        "/sha1", $certHash,
        "/tr", $timestampServer,
        "/td", "SHA256",
        $installer.FullName
    )

    Write-Host "  🔑 Signing: $($installer.Name)" -ForegroundColor Cyan
    $signResult = & $signTool $signArgs 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Digital signature applied" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Signing failed (non-fatal): $signResult" -ForegroundColor Yellow
    }
} else {
    Write-Host "[5/5] Digital signing skipped" -ForegroundColor Yellow
    if (-not $SkipSigning) {
        Write-Host "  ℹ Set SIGNTOOL_PATH and SIGN_CERTIFICATE_SHA1 env vars to enable signing" -ForegroundColor Cyan
    }
}

# ── Step 6: Generate checksum ──
$installer = Get-ChildItem "dist\FilePilot-AI-Setup-*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($installer) {
    $hash = Get-FileHash -Algorithm SHA256 -Path $installer.FullName
    $hashPath = "$($installer.DirectoryName)\$($installer.BaseName).sha256"
    $hash.Hash | Out-File -FilePath $hashPath -Encoding ascii
    Write-Host "  🔐 SHA256: $($hash.Hash.Substring(0, 16))... → $($hashPath | Split-Path -Leaf)" -ForegroundColor Cyan

    $installerSize = [math]::Round($installer.Length / 1MB, 2)
}

# ── Summary ──
$pyinstallerVer = pyinstaller --version 2>$null
Write-Host ""
Write-Host "=== Build Summary ===" -ForegroundColor Cyan
Write-Host "  Version    : $AppVersion"
Write-Host "  Timestamp  : $timestamp"
Write-Host "  PyInstaller: $pyinstallerVer"
Write-Host "  Inno Setup : $(Split-Path $isccPath -Parent | Split-Path -Leaf)"
if ($installer) {
    Write-Host "  Installer  : $($installer.Name) ($installerSize MB)"
}
Write-Host "====================" -ForegroundColor Cyan
