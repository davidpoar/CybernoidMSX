# Ejecuta Cybernoid en el emulador de Spectrum de z80emu (modo normal,
# sin agente) y captura la ventana.  En modo agente el emulador no genera
# las interrupciones de frame, asi que el juego no arranca.
#
# Uso: powershell -File capture_spectrum.ps1 [-Wait 90] [-PressSpace]
param(
    [int]$Wait = 90,
    [switch]$PressSpace,
    [string]$Out = "$PSScriptRoot\..\spectrum\captures"
)

$ErrorActionPreference = "Stop"
$emu = "C:\Dev\z80emu\spectrum\bin\Debug\net10.0\spectrum.exe"
$work = "C:\Users\rubbe\AppData\Local\Temp\opencode\spec-roms"
$tzx = "$work\Cybernoid.tzx"

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win {
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

if (-not (Test-Path $tzx)) { throw "no esta la cinta en $tzx" }
New-Item -ItemType Directory -Force -Path $Out | Out-Null

Get-Process spectrum -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

$proc = Start-Process -FilePath $emu -ArgumentList "-t", $tzx -WorkingDirectory $work -PassThru
Write-Host "emulador PID $($proc.Id); esperando $Wait s a que cargue la cinta..."

$deadline = (Get-Date).AddSeconds($Wait)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    $proc.Refresh()
    if ($proc.HasExited) { Write-Host "el emulador termino"; break }
    Write-Host ("  ... {0:N0} s restantes" -f ($deadline - (Get-Date)).TotalSeconds)
}

function Guardar([string]$nombre) {
    $proc.Refresh()
    $hwnd = $proc.MainWindowHandle
    if ($hwnd -eq 0) { throw "no hay ventana" }
    [void][Win]::SetForegroundWindow($hwnd)
    Start-Sleep -Milliseconds 500
    $r = New-Object Win+RECT
    [void][Win]::GetWindowRect($hwnd, [ref]$r)
    $w = $r.Right - $r.Left; $h = $r.Bottom - $r.Top
    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $dc = $g.GetHdc()
    [void][Win]::PrintWindow($hwnd, $dc, 2)
    $g.ReleaseHdc($dc); $g.Dispose()
    $path = Join-Path $Out "$nombre.png"
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Host "captura: $path ($w x $h)"
}

Guardar "spectrum_01"

if ($PressSpace) {
    Write-Host "pulsando ESPACIO..."
    $proc.Refresh()
    [void][Win]::SetForegroundWindow($proc.MainWindowHandle)
    Start-Sleep -Milliseconds 500
    [System.Windows.Forms.SendKeys]::SendWait(" ")
    Start-Sleep -Seconds 6
    Guardar "spectrum_02"
}

$proc | Stop-Process -Force -ErrorAction SilentlyContinue
