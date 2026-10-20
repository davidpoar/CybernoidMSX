# Captura la ventana del emulador MSX en un PNG.
# Uso: powershell -File capture_rom.ps1 [-Seconds 20] [-Out screen.png]
param(
    [int]$Seconds = 20,
    [string]$Out = "$PSScriptRoot\..\build\screen.png"
)

$ErrorActionPreference = "Stop"
$emu = "C:\Dev\z80emu\msx\bin\Debug\net10.0\msx.exe"
$rom = "C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms\cybernoid\cybernoid.rom"
$work = "C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms"

Add-Type -AssemblyName System.Drawing
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

if (-not (Test-Path $rom)) { throw "no esta la ROM en $rom" }

Get-Process msx -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

$proc = Start-Process -FilePath $emu -ArgumentList "-r", $rom, "--mapper", "ascii16" `
    -WorkingDirectory $work -PassThru
Write-Host "emulador PID $($proc.Id), esperando $Seconds s..."

$deadline = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 1
    $proc.Refresh()
    if ($proc.HasExited) { Write-Host "el emulador termino"; break }
}

$proc.Refresh()
$hwnd = $proc.MainWindowHandle
if ($hwnd -eq 0) { throw "no se encontro la ventana" }
[void][Win]::SetForegroundWindow($hwnd)
Start-Sleep -Milliseconds 700

$r = New-Object Win+RECT
[void][Win]::GetWindowRect($hwnd, [ref]$r)
$w = $r.Right - $r.Left
$h = $r.Bottom - $r.Top
Write-Host "ventana: $w x $h en ($($r.Left),$($r.Top))"

$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$dc = $g.GetHdc()
[void][Win]::PrintWindow($hwnd, $dc, 2)
$g.ReleaseHdc($dc)
$g.Dispose()

$outFull = [System.IO.Path]::GetFullPath($Out)
$bmp.Save($outFull, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Host "captura guardada en $outFull"

$proc | Stop-Process -Force -ErrorAction SilentlyContinue
