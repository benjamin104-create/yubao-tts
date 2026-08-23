#!/usr/bin/env node
/* Tiny dependency-free local server for testing web/index.html.
   Usage: node tools/serve_web.mjs [port] */
import http from 'node:http';
import {createReadStream, statSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'web');
const port = Number(process.argv[2] || 8765);
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8',
               '.css':'text/css; charset=utf-8','.png':'image/png','.jpg':'image/jpeg',
               '.jpeg':'image/jpeg','.svg':'image/svg+xml'};

http.createServer((req,res)=>{
  const pathname = decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname);
  const wanted = pathname === '/' ? '/index.html' : pathname;
  const file = path.resolve(root,'.' + wanted);
  if(file !== root && !file.startsWith(root + path.sep)){
    res.writeHead(403); res.end('Forbidden'); return;
  }
  try {
    if(!statSync(file).isFile()) throw new Error('not a file');
    res.writeHead(200, {'Content-Type':types[path.extname(file).toLowerCase()] || 'application/octet-stream',
                        'Cache-Control':'no-store'});
    createReadStream(file).pipe(res);
  } catch(e){ res.writeHead(404); res.end('Not found'); }
}).listen(port,'127.0.0.1',()=>console.log(`http://127.0.0.1:${port}`));
