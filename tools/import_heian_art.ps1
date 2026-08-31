param([string]$ProjectRoot=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
# Asset processing only: generated silhouettes -> crop, box-filter, fixed palette,
# binary alpha and bottom-center anchors. No new illustration is drawn here.
$refs=@([Drawing.Color].Assembly.Location,[Drawing.Bitmap].Assembly.Location,[Drawing.Imaging.PixelFormat].Assembly.Location)
$probe=[Drawing.Bitmap]::new(1,1);$probe.Dispose()
$refs+=@([AppDomain]::CurrentDomain.GetAssemblies() | Where-Object {$_.GetName().Name -match '^System\.(Drawing|Private\.Windows)'} | ForEach-Object {$_.Location})
Add-Type -ReferencedAssemblies ($refs | Select-Object -Unique) -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
public static class HeianSpriteImport {
  public static void Convert(string input,string output,int size,string[] hex) {
    var pal=Array.ConvertAll(hex,h=>Color.FromArgb(255,Int32.Parse(h,System.Globalization.NumberStyles.HexNumber)>>16&255,Int32.Parse(h,System.Globalization.NumberStyles.HexNumber)>>8&255,Int32.Parse(h,System.Globalization.NumberStyles.HexNumber)&255));
    using(var src=new Bitmap(input)) using(var dst=new Bitmap(size,size,PixelFormat.Format32bppArgb)) {
      int l=src.Width,t=src.Height,r=-1,b=-1;
      for(int y=0;y<src.Height;y++)for(int x=0;x<src.Width;x++)if(src.GetPixel(x,y).A>=245){l=Math.Min(l,x);r=Math.Max(r,x);t=Math.Min(t,y);b=Math.Max(b,y);}
      if(r<l)throw new Exception("No opaque silhouette: "+input);
      double scale=Math.Min((size-2.0)/(r-l+1),(size-1.0)/(b-t+1));
      int w=(int)Math.Round((r-l+1)*scale),h=(int)Math.Round((b-t+1)*scale),ox=(size-w)/2,oy=size-h;
      for(int y=0;y<h;y++)for(int x=0;x<w;x++) {
        double rr=0,gg=0,bb=0,aa=0;int n=0;
        int x0=l+(int)(x*(r-l+1.0)/w),x1=l+(int)((x+1)*(r-l+1.0)/w);
        int y0=t+(int)(y*(b-t+1.0)/h),y1=t+(int)((y+1)*(b-t+1.0)/h);
        for(int sy=y0;sy<y1;sy++)for(int sx=x0;sx<x1;sx++) {var p=src.GetPixel(sx,sy);n++;if(p.A<245)continue;aa++;rr+=p.R;gg+=p.G;bb+=p.B;}
        if(aa<n*.48||aa==0)continue;rr/=aa;gg/=aa;bb/=aa;
        int best=0;double score=Double.MaxValue;
        for(int i=0;i<pal.Length;i++){var c=pal[i];double d=(rr-c.R)*(rr-c.R)*.3+(gg-c.G)*(gg-c.G)*.5+(bb-c.B)*(bb-c.B)*.2;if(d<score){score=d;best=i;}}
        dst.SetPixel(x+ox,y+oy,pal[best]);
      }
      // A thin toe or tassel can be lost by area sampling. Keep the actual visible
      // silhouette on the grid baseline without stretching its proportions.
      int bottom=0;for(int y=0;y<size;y++)for(int x=0;x<size;x++)if(dst.GetPixel(x,y).A>0)bottom=y+1;
      using(var grounded=new Bitmap(size,size,PixelFormat.Format32bppArgb)) {
        for(int y=0;y<bottom;y++)for(int x=0;x<size;x++)grounded.SetPixel(x,y+size-bottom,dst.GetPixel(x,y));
        grounded.Save(output,ImageFormat.Png);
      }
    }
  }
}
'@
$source=Join-Path $ProjectRoot 'art_raw/heian'
$defs=@(
  @{id='b_genmaan';file='exec-274b36be-cda3-45b7-bfb3-8082eb3c6ab5.png';pal='101c3a 1d3468 2f57a0 4a86cf 382044 75407f a85aaa 565668 c8c8d4 e8edf4 7d5c3c ecd3ae a87a1e dcae35'},
  @{id='b_musashimaru';file='exec-346f67be-43e1-43ae-84d1-e05de765399a.png';pal='101c3a 1d3468 2b2b38 565668 757589 c8c8d4 e8edf4 6b1a1e 9c2b2b c94a3a 5e442c a87a1e dcae35 ecd3ae'},
  @{id='b_doll_heal';file='exec-c4cd842c-8f56-41d2-8d9f-08c2cbcf5db7.png';pal='101c3a 2b2b38 1e5230 2f7d45 4aa85e 79c97a 43301f 7d5c3c bb9668 ecd3ae c8c8d4 f7f5eb a87a1e dcae35'},
  @{id='b_doll_mage';file='exec-99c8ad39-d013-4b3f-8b6a-89f4a1e09c19.png';pal='101c3a 382044 573060 75407f a85aaa c8c8d4 ecd3ae f7f5eb 6b1a1e 9c2b2b c94a3a 43301f 7d5c3c a87a1e'},
  @{id='b_doll_tank';file='exec-1b3dfdbb-54d4-48c8-b148-c31b289718ed.png';pal='101c3a 1d3468 2f57a0 565668 757589 c8c8d4 ecd3ae 43301f 7d5c3c 9c7850 bb9668 382044 75407f a85aaa'},
  @{id='samurai_spirit';file='exec-c0d80892-648f-4d2b-9127-95b9f7d41fc3.png';pal='101c3a 1d3468 2f57a0 4a86cf 7cb8ea 1d6475 2f90a6 58c2cf a5ebeb 565668 c8c8d4 e8edf4 7d5c3c ecd3ae'},
  @{id='muramasa';file='exec-e2a78819-526d-490e-9359-520be5e45423.png';pal='101c3a 2b2b38 565668 757589 c8c8d4 7cb8ea 6b1a1e 9c2b2b a87a1e dcae35'}
)
$generated='C:\Users\X\.codex\generated_images\01a017ef-eb82-7e11-a070-ef5023481b05'
New-Item -ItemType Directory -Path $source -Force | Out-Null
foreach($d in $defs){
  $raw=Join-Path $source ($d.id+'.png')
  if(!(Test-Path -LiteralPath $raw)){Copy-Item -LiteralPath (Join-Path $generated $d.file) -Destination $raw}
  $rel=if($d.id -eq 'muramasa'){'web/art/item/weap09.png'}else{'web/art/boss/'+$d.id+'.png'}
  $size=if($d.id -eq 'muramasa'){32}else{48}
  [HeianSpriteImport]::Convert($raw,(Join-Path $ProjectRoot $rel),$size,($d.pal -split ' '))
  Write-Host "$($d.id) -> $rel ($size px)"
}
