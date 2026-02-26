# Atelier Desktop + Android

## Web/Electron

1. Set API URL (optional):
   - Copy `.env.example` to `.env`
2. Run:
   - `npm run dev`

## Android (Capacitor)

1. Install dependencies:
   - `npm install`
2. Set Android API URL:
   - Create `.env` with `VITE_API_BASE=http://10.0.2.2:9000` (Android emulator)
   - For physical-device or production builds, use a reachable HTTPS URL, for example:
     `VITE_API_BASE=https://atelier-api.yourdomain.com`
3. Initialize Android project once:
   - `npm run mobile:android:init`
4. Build and sync web bundle:
   - `npm run mobile:sync`
5. Open Android Studio project:
   - `npm run mobile:open:android`

### Scripted Android build with API URL injection

Use the root build script and inject API URL at build time:

```powershell
powershell -ExecutionPolicy Bypass -File C:\DjinnOS\scripts\build_android.ps1 `
  -Version v0.1.1-prod `
  -ApiBaseUrl https://atelier-api.yourdomain.com
```

This sets `VITE_API_BASE` for the `mobile:sync` step before Gradle packaging.

## Notes

- Backend must be reachable from emulator/device.
- For physical devices, use your LAN IP instead of `10.0.2.2`.
- Keep kernel and atelier-api running before using Android client.
- For distributed production APKs, do not use localhost URLs.
- Bundled privacy manifest path in app/web assets:
  - `/privacy-policy-manifest.json`
