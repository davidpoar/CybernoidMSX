# Captura la ventana del emulador MSX en un PNG.
# Uso: powershell -File capture_rom.ps1 [-Seconds 20] [-Out screen.png]
param(
    [int]$Seconds = 20,
    [string]$Out = "$PSScriptRoot\..\build\screen.png",
    [string]$PressKey = ""
)

$ErrorActionPreference = "Stop"
$emu = "C:\Dev\z80emu\msx\bin\Debug\net10.0\msx.exe"
$romSrc = "$PSScriptRoot\..\build\cybernoid.rom"
# Un directorio propio sin cintas: si el emulador encuentra una cinta
# en el directorio de trabajo la carga en vez de la ROM.
$work = "C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms\cybernoid-capture"
$rom = "$work\cybernoid.rom"
$bios = "C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms\vg8020_basic-bios1.rom"

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

if (-not (Test-Path $romSrc)) { throw "no esta la ROM en $romSrc" }
New-Item -ItemType Directory -Force -Path $work | Out-Null
Copy-Item $romSrc $rom -Force
Copy-Item $bios "$work\msx.rom" -Force

Start-Sleep -Milliseconds 500

$proc = Start-Process -FilePath $emu -ArgumentList "-r", $rom, "--mapper", "ascii16", "--autotype", $PressKey `
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
Write-Host "titulo: $($proc.MainWindowTitle)"

# El emulador arranca en pausa con --agent-port: hay que mandarle
# los frames para que la pantalla se dibuje.




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

if ($PressKey -ne "") {
    Write-Host "pulsando la tecla '$PressKey'..."
    $proc.Refresh()
    [void][Win]::SetForegroundWindow($proc.MainWindowHandle)
    Start-Sleep -Milliseconds 700
    # (la tecla se teclea con el autotype del emulador)
    Start-Sleep -Seconds 2
    
    Start-Sleep -Seconds 3

    $proc.Refresh()
    $hwnd = $proc.MainWindowHandle
    [void][Win]::SetForegroundWindow($hwnd)
    Start-Sleep -Milliseconds 700
    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $dc = $g.GetHdc()
    [void][Win]::PrintWindow($hwnd, $dc, 2)
    $g.ReleaseHdc($dc)
    $g.Dispose()
    $out2 = [System.IO.Path]::GetFullPath($Out) -replace '\.png$', '_2.png'
    $bmp.Save($out2, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Host "captura guardada en $out2"

    Start-Sleep -Seconds 3
    $proc.Refresh()
    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $dc = $g.GetHdc()
    [void][Win]::PrintWindow($hwnd, $dc, 2)
    $g.ReleaseHdc($dc)
    $g.Dispose()
    $out3 = [System.IO.Path]::GetFullPath($Out) -replace '\.png$', '_3.png'
    $bmp.Save($out3, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Host "captura guardada en $out3"
}

$proc | Stop-Process -Force -ErrorAction SilentlyContinue




