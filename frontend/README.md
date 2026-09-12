# Flood-Aware — Frontend

The production Next.js frontend for **Flood-Aware**, a grounded, evidence-based flood decision-support system for Swat district, Khyber Pakhtunkhwa.

This app is a client for the [Flood-Aware FastAPI backend](../backend) — real village/shelter data, real GIS/weather/forecast evidence, and real government-policy guidance, all grounded and cited, not fabricated.

## Pages

- **Home** (`/`) — live overview and navigation
- **Flood Guide** (`/agent`) — grounded, evidence-cited flood risk conversation for any village
- **Policy Advisor** (`/policy-advisor`) — government policy and disaster-management guidance, grounded in real PDMA/NDMP documents
- **Situation Room** (`/situation-room`) — real village/shelter data and an interactive map

## Getting started

The FastAPI backend must be running first (see the [backend README](../backend)).

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Configure the backend URL via `.env.local` (see `.env.example`) if it isn't running at the default `http://localhost:8000`.

## Stack

Next.js 16 (App Router) · TypeScript · Tailwind CSS v4 · shadcn/ui · react-leaflet

## Note

This is the production frontend, replacing the earlier Streamlit dashboard (`../dashboard`), which is retained as a working reference until this app is fully deployed.