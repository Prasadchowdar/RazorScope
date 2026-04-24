# RazorScope Frontend

This frontend is the customer-facing surface for RazorScope. It includes:

- animated landing page
- sign in and sign up flows
- analytics dashboard
- setup guide
- Razorpay connection and historical backfill controls

## Run Locally

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`.

## Build

```powershell
npm run build
```

## Notes

- Landing, login, register, and dashboard are split so the first load is lighter
- The authenticated product depends on the API being reachable at the configured base URL
