#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const frontendDir = __dirname;

function ensureStandaloneAssetPath(source, target) {
  if (!fs.existsSync(source) || fs.existsSync(target)) {
    return;
  }

  fs.mkdirSync(path.dirname(target), { recursive: true });

  try {
    fs.symlinkSync(path.relative(path.dirname(target), source), target, 'dir');
  } catch {
    fs.cpSync(source, target, { recursive: true });
  }
}

ensureStandaloneAssetPath(
  path.join(frontendDir, '.next', 'static'),
  path.join(frontendDir, '.next', 'standalone', '.next', 'static'),
);
ensureStandaloneAssetPath(
  path.join(frontendDir, 'public'),
  path.join(frontendDir, '.next', 'standalone', 'public'),
);

// Set default PORT if not already set
if (!process.env.PORT) {
  process.env.PORT = '8502';
}

// Start the Next.js standalone server
require('./.next/standalone/server.js');
