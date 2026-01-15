#!/usr/bin/env node

// Set default PORT if not already set
if (!process.env.PORT) {
  process.env.PORT = '8502';
}

// Start the Next.js standalone server
require('./.next/standalone/server.js');
