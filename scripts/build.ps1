$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv is required. Install it from https://docs.astral.sh/uv/"
}

uv sync --dev
uv run python scripts/build.py @args
