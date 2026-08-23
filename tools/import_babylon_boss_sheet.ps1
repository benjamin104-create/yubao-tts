param(
  [Parameter(Mandatory=$true)][string]$SourceSheet,
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

# The approved source sheet is exactly three equal horizontal cells:
# Lamassu door / artisan machine / horned hall lord.
$specs = @(
  @{Id='b_keeper';   Col=0; FitW=46; FitH=46},
  @{Id='b_artisan';  Col=1; FitW=47; FitH=46},
  @{Id='b_hallking'; Col=2; FitW=47; FitH=45}
)

function Get-SubjectBounds([Drawing.Bitmap]$bmp,[Drawing.Rectangle]$cell){
  $minX=$cell.Right;$minY=$cell.Bottom;$maxX=-1;$maxY=-1
  for($y=$cell.Top;$y -lt $cell.Bottom;$y+=2){for($x=$cell.Left;$x -lt $cell.Right;$x+=2){
    $p=$bmp.GetPixel($x,$y)
    $nearWhite=($p.R -ge 238 -and $p.G -ge 238 -and $p.B -ge 238)
    if($nearWhite){continue}
    $minX=[Math]::Min($minX,$x);$minY=[Math]::Min($minY,$y)
    $maxX=[Math]::Max($maxX,$x);$maxY=[Math]::Max($maxY,$y)
  }}
  if($maxX -lt 0){throw "No subject found in cell $cell"}
  return [Drawing.Rectangle]::FromLTRB($minX,$minY,$maxX+2,$maxY+2)
}

$src=[Drawing.Bitmap]::FromFile((Resolve-Path -LiteralPath $SourceSheet))
try{
  for($i=0;$i -lt $specs.Count;$i++){
    $s=$specs[$i]
    $x0=[int][Math]::Floor($src.Width*$s.Col/3.0)
    $x1=[int][Math]::Floor($src.Width*($s.Col+1)/3.0)
    $cell=[Drawing.Rectangle]::FromLTRB($x0,0,$x1,$src.Height)
    $box=Get-SubjectBounds $src $cell
    $scale=[Math]::Min($s.FitW/$box.Width,$s.FitH/$box.Height)
    $dw=[Math]::Max(1,[int][Math]::Floor($box.Width*$scale))
    $dh=[Math]::Max(1,[int][Math]::Floor($box.Height*$scale))
    $dx=[int][Math]::Floor((48-$dw)/2);$dy=48-$dh

    $out=[Drawing.Bitmap]::new(48,48,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g=[Drawing.Graphics]::FromImage($out)
    try{
      $g.CompositingMode=[Drawing.Drawing2D.CompositingMode]::SourceCopy
      $g.InterpolationMode=[Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
      $g.PixelOffsetMode=[Drawing.Drawing2D.PixelOffsetMode]::Half
      $g.DrawImage($src,[Drawing.Rectangle]::new($dx,$dy,$dw,$dh),$box,[Drawing.GraphicsUnit]::Pixel)
    } finally {$g.Dispose()}

    # Turn the white cell background transparent and harden every surviving edge.
    for($y=0;$y -lt 48;$y++){for($x=0;$x -lt 48;$x++){
      $p=$out.GetPixel($x,$y)
      if($p.R -ge 226 -and $p.G -ge 226 -and $p.B -ge 226){
        $out.SetPixel($x,$y,[Drawing.Color]::Transparent)
      } elseif($p.A -gt 0){
        $out.SetPixel($x,$y,[Drawing.Color]::FromArgb(255,$p.R,$p.G,$p.B))
      }
    }}
    $dest=Join-Path $ProjectRoot "web/art/boss/$($s.Id).png"
    $out.Save($dest,[Drawing.Imaging.ImageFormat]::Png);$out.Dispose()
    Write-Host "imported $($s.Id): $box -> ${dw}x${dh}"
  }
} finally {$src.Dispose()}

# Map colors to the fixed art direction and rebuild the 10x3 sheets from the
# approved still silhouettes in the companion normalization pass.
& (Join-Path $PSScriptRoot 'normalize_boss_palette.ps1') -ProjectRoot $ProjectRoot
