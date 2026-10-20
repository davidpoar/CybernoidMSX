# Analiza la captura PNG: dice cuanto ocupa la pantalla y que colores hay.
param(
    [string]$In = "$PSScriptRoot\..\build\screen.png"
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$bmp = [System.Drawing.Bitmap]::FromFile([System.IO.Path]::GetFullPath($In))
Write-Host "imagen: $($bmp.Width) x $($bmp.Height)"

$counts = @{}
$minX = 9999; $maxX = -1; $minY = 9999; $maxY = -1
for ($y = 0; $y -lt $bmp.Height; $y++) {
    for ($x = 0; $x -lt $bmp.Width; $x++) {
        $c = $bmp.GetPixel($x, $y)
        if ($c.R -gt 20 -or $c.G -gt 20 -or $c.B -gt 20) {
            $k = "{0:X2}{1:X2}{2:X2}" -f $c.R, $c.G, $c.B
            if ($counts.ContainsKey($k)) { $counts[$k]++ } else { $counts[$k] = 1 }
            if ($x -lt $minX) { $minX = $x }
            if ($x -gt $maxX) { $maxX = $x }
            if ($y -lt $minY) { $minY = $y }
            if ($y -gt $maxY) { $maxY = $y }
        }
    }
}
Write-Host "area con color: x $minX..$maxX  y $minY..$maxY  ($($maxX-$minX+1) x $($maxY-$minY+1))"
Write-Host "colores:"
$counts.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object {
    Write-Host ("   #{0}  {1,8} pixeles" -f $_.Key, $_.Value)
}
$bmp.Dispose()
