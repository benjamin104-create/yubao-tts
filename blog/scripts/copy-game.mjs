import { access, cp, mkdir, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const source = new URL('../../web/', import.meta.url);
const destination = new URL('../dist/game/', import.meta.url);
const dist = new URL('../dist/', import.meta.url);

await access(new URL('index.html', source));
await mkdir(dist, { recursive: true });
await rm(destination, { recursive: true, force: true });
await cp(source, destination, { recursive: true });

console.log(`Copied game to ${fileURLToPath(destination)}`);
