import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.quantumquackery.atelier",
  appName: "Quantum Quackery Virtual Atelier",
  webDir: "dist",
  server: {
    cleartext: true
  }
};

export default config;

