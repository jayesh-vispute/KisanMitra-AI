/**
 * api.js — Centralized API layer using axios.
 * All parameters are URL-encoded automatically by axios.
 */
import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api",
  timeout: 30000,
});

// ─── Market API ──────────────────────────────────────────────────────────────

export const marketAPI = {
  getStates: () =>
    API.get("/market/states").then((r) => r.data),

  getDistricts: (state) =>
    API.get("/market/districts", { params: { state } }).then((r) => r.data),

  getMandis: (state, district) =>
    API.get("/market/mandis", { params: { state, district } }).then((r) => r.data),

  getCommodities: (state, district, market) =>
    API.get("/market/commodities", { params: { state, district, market } }).then((r) => r.data),

  getPrices: (state, district, market, commodity) =>
    API.get("/market/prices", { params: { state, district, market, commodity } }).then((r) => r.data),
};

// ─── Forecast API ────────────────────────────────────────────────────────────

export const forecastAPI = {
  getPredict: (commodity, market, horizon = 7) =>
    API.get("/predict", { params: { commodity, market, horizon } }).then((r) => r.data),
};

// ─── Chat API ────────────────────────────────────────────────────────────────

export const chatAPI = {
  sendMessage: (message, commodity, mandi, language = "en") =>
    API.post("/chat", { message, commodity, mandi, language }).then((r) => r.data),
};

// ─── Weather API ─────────────────────────────────────────────────────────────

export const weatherAPI = {
  getWeather: (mandi) =>
    API.get("/weather", { params: { mandi } }).then((r) => r.data),
};

// ─── Backward-compatible named exports used by existing components ───────────

/** Used by Navbar.jsx (not rewritten) */
export const getDashboardSummary = () =>
  API.get("/market/prices", { params: { commodity: "Onion", market: "Nashik" } })
    .then((r) => ({ last_updated: new Date().toISOString(), ...r.data }))
    .catch(() => ({ last_updated: new Date().toISOString() }));

/** Used by Alerts.jsx (not rewritten) */
export const getAlerts = () =>
  Promise.resolve({ alerts: [] });

/** Used by Forecast.jsx (not rewritten) */
export const getPredict = (commodity, mandi, horizon = 7) =>
  forecastAPI.getPredict(commodity, mandi, horizon);

export const getCropHealth = (mandi) =>
  API.get("/crop-health", { params: { mandi } }).then((r) => r.data);

export const getFarmerAdvisory = (commodity, mandi) =>
  API.get("/farmer-advisory", { params: { commodity, mandi } }).then((r) => r.data);
