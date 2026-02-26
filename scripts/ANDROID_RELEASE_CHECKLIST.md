# Android Same-Day Distribution Checklist

## 1) Deploy backend endpoints first

- Host `atelier-api` on a reachable URL (example: `https://atelier-api.yourdomain.com`).
- Host kernel service on a reachable URL (example: `https://kernel.yourdomain.com`).
- Configure API environment:
  - `KERNEL_BASE_URL=https://kernel.yourdomain.com`
  - `DATABASE_URL=<production-db-url>`
  - `CORS_ALLOWED_ORIGINS=<allowed-origins>`
- Verify:
  - `GET /health` on API returns 200.
  - API can reach kernel `/events` and `/observe`.

## 2) Build signed Android artifacts with production API URL

- Ensure signing vars are set:
  - `ATELIER_ANDROID_KEYSTORE`
  - `ATELIER_ANDROID_KEYSTORE_PASSWORD`
  - `ATELIER_ANDROID_KEY_ALIAS`
  - `ATELIER_ANDROID_KEY_PASSWORD`
- Run:

```powershell
powershell -ExecutionPolicy Bypass -File C:\DjinnOS\scripts\build_android.ps1 `
  -Version v0.1.1-prod `
  -ApiBaseUrl https://atelier-api.yourdomain.com
```

- Confirm artifacts exist under:
  - `apps/atelier-desktop/release/android/v0.1.1-prod/`
  - `app-release.apk`
  - `app-release.aab`

## 3) Smoke-test release APK on a real device

- Install `app-release.apk`.
- Open app and verify:
  - Privacy manifest page loads.
  - `/v1/access/artisan-id/status` returns live data.
  - Gate verify/issue endpoints work.
  - Workshop functions that depend on API return data.

## 4) Choose distribution path

- Fastest same-day:
  - Share signed `app-release.apk` directly.
  - User enables install from unknown sources.
- Recommended:
  - Upload `app-release.aab` to Google Play Internal Testing.
  - Invite testers by email.

## 5) Pre-share final checks

- Production URL is HTTPS and not localhost.
- API and kernel processes are up and monitored.
- CORS includes client origins in use.
- App version/tag recorded for rollback.
- Keep previous known-good APK available.
