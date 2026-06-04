<#
.SYNOPSIS
    Compile each LaTeX template with Tectonic to catch engine/font/Croatian regressions.
.DESCRIPTION
    Renders the master via render_template.py (the same path latex_architect uses),
    compiles with Tectonic, and fails on a missing PDF or dropped Croatian glyphs.
.EXAMPLE
    .\tests\compile-template.ps1
    .\tests\compile-template.ps1 fsb-seminar
#>
param([string[]]$Formats)

$ErrorActionPreference = "Stop"
$brainRoot = Split-Path -Parent $PSScriptRoot

if (-not $Formats -or $Formats.Count -eq 0) {
    $Formats = @("fsb-seminar", "fsb-thesis", "fsb-paper", "fsb-presentation")
}

if (-not (Get-Command tectonic -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: tectonic not found — required for the template compile test." -ForegroundColor Red
    exit 1
}

$fail = 0
foreach ($fmt in $Formats) {
    Write-Host "=== $fmt ===" -ForegroundColor Cyan
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("lr_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 10))
    New-Item -ItemType Directory -Path (Join-Path $tmp ".ai\config") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $tmp "docs\build") -Force | Out-Null

    @"
name: "Test Projekt"
latex_format: "$fmt"
author_name: "Ivan Horvat"
course_name: "TEST KOLEGIJ ČĆŽŠĐ"
seminar_title: "Naslov rada s hrvatskim slovima: žđšćč ŽĐŠĆČ"
seminar_title_short: "Kratki naslov žđšćč"
professor_title: "Prof. dr. sc."
professor_name: "Ana Marić"
include_lof: true
include_lot: true
"@ | Set-Content (Join-Path $tmp ".ai\config\project.yaml") -Encoding utf8

    python (Join-Path $brainRoot "scripts\render_template.py") `
        --project-root $tmp --format $fmt --scaffold --fill-stubs --force
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  RENDER FAILED" -ForegroundColor Red; $fail = 1
        Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue; continue
    }

    Push-Location $tmp
    tectonic -X compile docs/main.tex --outdir docs/build --keep-logs *> "$tmp\compile.out"
    $rc = $LASTEXITCODE
    Pop-Location

    $log = Join-Path $tmp "docs\build\main.log"
    $pdf = Join-Path $tmp "docs\build\main.pdf"

    if ($rc -ne 0) {
        Write-Host "  COMPILE FAILED (rc=$rc)" -ForegroundColor Red
        Get-Content "$tmp\compile.out" -Tail 25; $fail = 1
    } elseif (-not (Test-Path $pdf)) {
        Write-Host "  NO PDF produced" -ForegroundColor Red
        Get-Content "$tmp\compile.out" -Tail 25; $fail = 1
    } else {
        # Exclude benign Beamer "nullfont" artefacts (char typeset before a font is active).
        $miss = @()
        if (Test-Path $log) {
            $miss = Select-String -Path $log -Pattern "Missing character" |
                Where-Object { $_.Line -notmatch "nullfont" }
        }
        if ($miss.Count -gt 0) {
            Write-Host "  FAIL: $($miss.Count) 'Missing character' warnings (Croatian glyphs dropped):" -ForegroundColor Red
            $miss | Select-Object -First 3 | ForEach-Object { Write-Host "    $($_.Line)" }
            $fail = 1
        } else {
            Write-Host "  OK: PDF built, no missing characters" -ForegroundColor Green
        }
    }
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}

if ($fail -ne 0) {
    Write-Host "TEMPLATE COMPILE TEST: FAILED" -ForegroundColor Red
} else {
    Write-Host "TEMPLATE COMPILE TEST: PASSED" -ForegroundColor Green
}
exit $fail
