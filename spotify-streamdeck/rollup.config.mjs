import typescript from "@rollup/plugin-typescript";
import resolve from "@rollup/plugin-node-resolve";
import commonjs from "@rollup/plugin-commonjs";

export default {
  input: "src/plugin.ts",
  output: {
    file: "com.leon.spotifycontrol.sdPlugin/bin/plugin.js",
    format: "cjs",
    sourcemap: true,
    interop: "auto",
  },
  plugins: [
    typescript(),
    resolve({ exportConditions: ["node"] }),
    commonjs(),
  ],
  // node: built-ins only -- bundle everything else, including the SDK,
  // so Rollup can resolve ESM/CJS default-export interop itself rather
  // than leaving a raw require() that Node may not unwrap correctly.
  external: ["node:net", "node:events"],
};
