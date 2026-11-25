import { cpSync } from 'node:fs'

// The standalone server needs the same static assets copied by the Docker build.
const frontend = new URL('../', import.meta.url)
for (const directory of ['public', '.next/static']) {
  cpSync(new URL(directory, frontend), new URL(`.next/standalone/${directory}`, frontend), {
    recursive: true,
  })
}
await import('../start-server.js')
