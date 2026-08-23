param(
  [Parameter(Mandatory=$true)][string[]]$Source,
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
  [int]$Width = 1200,
  [int]$Height = 800,
  [int]$Quality = 84
)

$ErrorActionPreference = 'Stop'
if ($Source.Count -ne 4) { throw 'Exactly four source images are required.' }

$root = [System.IO.Path]::GetFullPath($ProjectRoot)
$rawDir = Join-Path $root 'art_raw\prologue-charcoal-v1'
$webDir = Join-Path $root 'web\art\promo'
New-Item -ItemType Directory -Force -Path $rawDir, $webDir | Out-Null

Add-Type -AssemblyName System.Drawing
$jpgCodec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() |
  Where-Object MimeType -eq 'image/jpeg' |
  Select-Object -First 1
$enc = New-Object System.Drawing.Imaging.EncoderParameters(1)
$enc.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter(
  [System.Drawing.Imaging.Encoder]::Quality, [long]$Quality)

$names = @('tower-build','transport','unconscious','awakening')
for ($i = 0; $i -lt 4; $i++) {
  $src = [System.IO.Path]::GetFullPath($Source[$i])
  if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { throw "Missing source: $src" }

  Copy-Item -LiteralPath $src -Destination (Join-Path $rawDir ("{0}.png" -f $names[$i])) -Force
  $in = [System.Drawing.Image]::FromFile($src)
  try {
    $out = New-Object System.Drawing.Bitmap($Width, $Height)
    try {
      $g = [System.Drawing.Graphics]::FromImage($out)
      try {
        $g.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
        $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $g.DrawImage($in, 0, 0, $Width, $Height)
      } finally { $g.Dispose() }
      $dest = Join-Path $webDir ("prologue-charcoal-{0}-v1.jpg" -f ($i + 1))
      $out.Save($dest, $jpgCodec, $enc)
      Write-Host ("{0}  {1} bytes" -f $dest, (Get-Item -LiteralPath $dest).Length)
    } finally { $out.Dispose() }
  } finally { $in.Dispose() }
}

$enc.Dispose()
