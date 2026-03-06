Ko's Labyrnth Atelier - Quickstart
==================================

What this gives you:
- One installer script that downloads and unpacks the suite zip.
- One launcher script with desktop/start menu shortcuts.
- One click-through setup wizard for non-technical users.
- Local backend bundle (API + kernel runtime payload) installed by default.
- Bundled Python wheelhouse for offline-first dependency bootstrap.

Files:
- Install-Atelier.ps1
- Launch-Atelier.ps1
- Launch-Atelier.exe
- Setup-Wizard.ps1
- Setup-Wizard.cmd
- config.template.json
- icon.ico

Wizard install (easiest):
1) Extract this zip.
2) Double-click Setup-Wizard.cmd
3) Fill in suite URL or choose local zip, then click Install.

Install (recommended):
1) Open PowerShell.
2) Run:
   powershell -ExecutionPolicy Bypass -File .\Install-Atelier.ps1 -DownloadUrl "<YOUR_SUITE_ZIP_URL>" -RunAfterInstall

GitHub Releases URL format (recommended):
   https://github.com/<OWNER>/<REPO>/releases/download/<TAG>/<SUITE_ASSET>.zip

Install from a local zip:
   powershell -ExecutionPolicy Bypass -File .\Install-Atelier.ps1 -SuiteZipPath "C:\path\atelier-suite.zip" -RunAfterInstall

Default install folder:
- %LOCALAPPDATA%\KosLabyrnth\Atelier

After install:
- Desktop shortcut: Ko's Labyrnth Atelier
- Start Menu shortcut: Ko's Labyrnth > Ko's Labyrnth Atelier
- Local API/KERNEL startup is the default behavior on launch.

Notes:
- If you want remote services instead, edit config.json in the install folder.
