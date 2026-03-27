#!/usr/bin/env node

/**
 * Build script for Vercel deployment
 * Injects environment variables into config.js
 */

const fs = require("fs");
const path = require("path");

// Get API_BASE from environment variable or use default
const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

console.log("🔨 Building frontend configuration...");
console.log("📍 API_BASE:", API_BASE);

// Generate config.js with injected environment variables
const configContent = `// Configuration injected at build time
window.__CONFIG__ = {
  api_base: '${API_BASE}',
};

console.log('✓ Configuration loaded:', window.__CONFIG__);
`;

// Write config.js
const configPath = path.join(__dirname, "config.js");
fs.writeFileSync(configPath, configContent, "utf8");

console.log("✓ config.js generated successfully");
console.log("📄 Location:", configPath);
console.log("");
