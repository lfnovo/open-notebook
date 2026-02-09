import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  // Browser globals for client code (avoid no-undef for window, sessionStorage)
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      globals: {
        window: "readonly",
        sessionStorage: "readonly",
        document: "readonly",
      },
    },
  },
  // Node globals for standalone server script
  {
    files: ["start-server.js"],
    languageOptions: {
      globals: {
        process: "readonly",
        require: "readonly",
        __dirname: "readonly",
        __filename: "readonly",
        module: "readonly",
      },
    },
  },
];

export default eslintConfig;
