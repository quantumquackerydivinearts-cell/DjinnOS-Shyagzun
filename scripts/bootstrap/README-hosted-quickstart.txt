Ko's Labyrnth Hosted Atelier - Quickstart
=========================================

What this gives you:
- One installer script for the Hosted Atelier Stack.
- One hosted setup wizard for managed deployments.
- One desktop install configured for remote API/kernel endpoints.
- One bundled hosted-deployment folder containing docker-compose, Dockerfiles, and env template.

Files:
- Install-Hosted-Atelier.ps1
- Setup-Hosted-Wizard.ps1
- Setup-Hosted-Wizard.cmd
- Launch-Atelier.ps1
- Launch-Atelier.exe
- config.hosted.template.json
- icon.ico

Wizard install:
1) Extract this zip.
2) Double-click Setup-Hosted-Wizard.cmd
3) Choose the hosted suite zip or hosted download URL.
4) Enter your hosted API and kernel URLs.
5) Click Install Hosted Suite.

Current hosted defaults:
- API: https://djinnos-shyagzun-atelier-api.onrender.com
- Kernel: https://atelier-api.quantumquackery.com

Default install folder:
- %LOCALAPPDATA%\KosLabyrnth\Atelier-Hosted

Notes:
- This is not the local/offline installer.
- This installer expects atelier-hosted-suite-*.zip
- Docker deployment assets are copied into the install under hosted-deployment.
