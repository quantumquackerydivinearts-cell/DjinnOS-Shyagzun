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
3. Initialize Android project once:
   - `npm run mobile:android:init`
4. Build and sync web bundle:
   - `npm run mobile:sync`
5. Open Android Studio project:
   - `npm run mobile:open:android`

## Notes

- Backend must be reachable from emulator/device.
- For physical devices, use your LAN IP instead of `10.0.2.2`.
- Keep kernel and atelier-api running before using Android client.
- Bundled privacy manifest path in app/web assets:
  - `/privacy-policy-manifest.json`
