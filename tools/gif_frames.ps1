# Extrae los frames de un GIF animado como PNG usando System.Drawing.
# Uso: powershell -File gif_frames.ps1 <gif> <carpeta> [maximo]
param(
    [Parameter(Mandatory = $true)][string]$Gif,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int]$Max = 60
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$img = [System.Drawing.Image]::FromFile((Resolve-Path $Gif))
$dim = New-Object System.Drawing.Imaging.FrameDimension($img.FrameDimensionsList[0])
$n = $img.GetFrameCount($dim)
Write-Host "el GIF tiene $n frames"

for ($i = 0; $i -lt [Math]::Min($n, $Max); $i++) {
    $img.SelectActiveFrame($dim, $i)
    $bmp = New-Object System.Drawing.Bitmap $img.Width, $img.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.DrawImage($img, 0, 0, $img.Width, $img.Height)
    $g.Dispose()
    $path = Join-Path $OutDir ("frame_{0:D3}.png" -f $i)
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
}
$img.Dispose()
Write-Host "guardados $([Math]::Min($n, $Max)) frames en $OutDir"
