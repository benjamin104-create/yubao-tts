param([string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'

# Final deterministic palette pass for the four late-added bosses. Image
# generation supplies the silhouette; the shared game palette makes separate
# batches read as one SNES-era art direction.
Add-Type -AssemblyName System.Drawing

$StillPalette = @(
  '0d0d12','1a1a24','2b2b38','3d3d4d','565668','757589','c8c8d4',
  '2a1d14','43301f','5e442c','7d5c3c','9c7850','bb9668','ecd3ae',
  '6b1a1e','9c2b2b','c94a3a','e87a4a','f5a95e',
  '1e5230','2f7d45','4aa85e','79c97a',
  '101c3a','1d3468','2f57a0','4a86cf','7cb8ea',
  '6b4a12','a87a1e','dcae35','f5dc7a'
)
$AnimPalette = @(
  '0d0d12','1a1a24','2b2b38','3d3d4d','565668','757589','c8c8d4','e8edf4','f7f5eb',
  '2a1d14','43301f','5e442c','7d5c3c','9c7850','bb9668','ecd3ae',
  '6b1a1e','9c2b2b','c94a3a','e87a4a','f5a95e',
  '1e5230','2f7d45','4aa85e','79c97a',
  '101c3a','1d3468','2f57a0','4a86cf','7cb8ea',
  '382044','573060','75407f','a85aaa','d978c4','f2b2df',
  '1d6475','2f90a6','58c2cf','a5ebeb',
  '6b4a12','a87a1e','dcae35','f5dc7a'
)
$BossPalettes = @{
  b_keeper = @('0d0d12','101c3a','1d3468','2f57a0','4a86cf','565668','757589','c8c8d4','ecd3ae','2a1d14','7d5c3c','a87a1e','dcae35','f5dc7a')
  b_lord = @('0d0d12','101c3a','1d3468','2f57a0','4a86cf','7cb8ea','e8edf4','f7f5eb','1d6475','2f90a6','58c2cf','a5ebeb','565668','c8c8d4')
  b_artisan = @('0d0d12','2a1d14','43301f','5e442c','7d5c3c','9c7850','bb9668','ecd3ae','101c3a','2f57a0','4a86cf','7cb8ea','565668','c8c8d4')
  b_hallking = @('0d0d12','101c3a','1d3468','2f57a0','4a86cf','6b4a12','a87a1e','dcae35','f5dc7a','757589','c8c8d4','ecd3ae','5e442c','9c7850')
}

function Convert-HexPalette($hexes) {
  return @($hexes | ForEach-Object {
    [Drawing.Color]::FromArgb(255,
      [Convert]::ToInt32($_.Substring(0,2),16),
      [Convert]::ToInt32($_.Substring(2,2),16),
      [Convert]::ToInt32($_.Substring(4,2),16))
  })
}

function Convert-ToLab([Drawing.Color]$c) {
  $v=@(
    ([double]$c.R / 255.0),
    ([double]$c.G / 255.0),
    ([double]$c.B / 255.0)
  )
  for($i=0;$i -lt 3;$i++){
    $v[$i]=if($v[$i] -le .04045){$v[$i]/12.92}else{[Math]::Pow(($v[$i]+.055)/1.055,2.4)}
  }
  $x=($v[0]*.4124+$v[1]*.3576+$v[2]*.1805)/.95047
  $y= $v[0]*.2126+$v[1]*.7152+$v[2]*.0722
  $z=($v[0]*.0193+$v[1]*.1192+$v[2]*.9505)/1.08883
  $xyz=@($x,$y,$z)
  for($i=0;$i -lt 3;$i++){
    $xyz[$i]=if($xyz[$i] -gt .008856){[Math]::Pow($xyz[$i],1.0/3.0)}else{7.787*$xyz[$i]+16.0/116.0}
  }
  return [PSCustomObject]@{
    L = 116*$xyz[1]-16
    Ca = 500*($xyz[0]-$xyz[1])
    Cb = 200*($xyz[1]-$xyz[2])
  }
}

function Find-Nearest([Drawing.Color]$source,$palette,$labs) {
  $s=Convert-ToLab $source; $best=0; $bestD=[double]::PositiveInfinity
  for($i=0;$i -lt $palette.Count;$i++){
    $d=[Math]::Pow($s.L-$labs[$i].L,2)+[Math]::Pow($s.Ca-$labs[$i].Ca,2)+[Math]::Pow($s.Cb-$labs[$i].Cb,2)
    if($d -lt $bestD){$bestD=$d;$best=$i}
  }
  return $palette[$best]
}

function Normalize-Image([string]$path,$paletteHex,[bool]$ground) {
  $palette=Convert-HexPalette $paletteHex
  $labs=@($palette | ForEach-Object { Convert-ToLab $_ })
  $src=[Drawing.Bitmap]::FromFile($path)
  try{
    $bottom=0
    for($y=0;$y -lt $src.Height;$y++){for($x=0;$x -lt $src.Width;$x++){
      if($src.GetPixel($x,$y).A -ge 128){$bottom=[Math]::Max($bottom,$y+1)}
    }}
    $dy=if($ground){$src.Height-$bottom}else{0}
    $out=[Drawing.Bitmap]::new($src.Width,$src.Height,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $cache=@{};$used=@{}
    try{
      for($y=0;$y -lt $src.Height;$y++){for($x=0;$x -lt $src.Width;$x++){
        $p=$src.GetPixel($x,$y); if($p.A -lt 128){continue}
        $key='{0},{1},{2}' -f $p.R,$p.G,$p.B
        if(!$cache.ContainsKey($key)){$cache[$key]=Find-Nearest $p $palette $labs}
        $ny=$y+$dy; if($ny -lt $out.Height){$out.SetPixel($x,$ny,$cache[$key]);$used[$cache[$key].ToArgb()]=$true}
      }}
      if($used.Count -lt 8 -or $used.Count -gt 14){throw "$(Split-Path $path -Leaf): expected 8-14 colors, got $($used.Count)"}
      $tmp=$path+'.tmp.png';$out.Save($tmp,[Drawing.Imaging.ImageFormat]::Png)
    } finally {$out.Dispose()}
  } finally {$src.Dispose()}
  Move-Item -LiteralPath ($path+'.tmp.png') -Destination $path -Force
  return $used.Count
}

function Build-Animation([string]$stillPath,[string]$animPath) {
  $sprite=[Drawing.Bitmap]::FromFile($stillPath)
  try{
    $sheet=[Drawing.Bitmap]::new(480,144,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g=[Drawing.Graphics]::FromImage($sheet)
    try{
      $g.CompositingMode=[Drawing.Drawing2D.CompositingMode]::SourceCopy
      $g.InterpolationMode=[Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
      $g.PixelOffsetMode=[Drawing.Drawing2D.PixelOffsetMode]::Half
      for($row=0;$row -lt 3;$row++){for($col=0;$col -lt 10;$col++){
        $dx=@(0,0,-1,0,1,0,1,-1,0,1)[$col]
        $dy=@(0,-1,0,-1,0,-1,0,-1,0,1)[$col]
        $w=if($col -in 6,7){49}else{48}
        $h=if($col -eq 7){49}else{48}
        $g.DrawImage($sprite,[Drawing.Rectangle]::new($col*48+$dx,$row*48+$dy,$w,$h),0,0,48,48,[Drawing.GraphicsUnit]::Pixel)
      }}
      $sheet.Save($animPath,[Drawing.Imaging.ImageFormat]::Png)
    } finally {$g.Dispose();$sheet.Dispose()}
  } finally {$sprite.Dispose()}
}

foreach($id in @('b_keeper','b_lord','b_artisan','b_hallking')){
  $still=Join-Path $ProjectRoot "web/art/boss/$id.png"
  $anim=Join-Path $ProjectRoot "web/art/anim/boss/$id.png"
  $sc=Normalize-Image $still $BossPalettes[$id] $true
  Build-Animation $still $anim
  $ac=Normalize-Image $anim $AnimPalette $false
  Write-Host "$id : still $sc colors; animation $ac colors"
}
