import { useState, useEffect } from "react";
import { forecastAPI } from "../utils/api";
import { useSettings } from "../contexts/SettingsContext";
import { useTranslation } from "../locales/translations";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from "recharts";
import { TrendingUp, TrendingDown, Database, Activity } from "lucide-react";

export default function Dashboard({ selection }) {
  const { language } = useSettings();
  const { t } = useTranslation(language);

  const { commodity, mandi, horizon } = selection || {};
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!commodity || !mandi) {
      setError(null);
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);

    forecastAPI
      .getPredict(commodity, mandi, horizon || 7)
      .then((result) => {
        if (result.error && (!result.history || result.history.length === 0)) {
          setError(result.error);
        } else {
          setData(result);
        }
      })
      .catch((err) => {
        console.error("Dashboard fetch error:", err);
        setError("Could not connect to the server. Please try again later.");
      })
      .finally(() => setLoading(false));
  }, [commodity, mandi, horizon]);

  // ─── Welcome screen ─────────────────────────────────────────────────────────

  if (!commodity || !mandi) {
    return (
      <div className="flex items-center justify-center h-full min-h-[70vh]">
        <div className="text-center max-w-lg p-10 bg-white/60 backdrop-blur-xl border border-white rounded-3xl shadow-2xl shadow-gray-200/50">
          <div className="w-24 h-24 mx-auto bg-emerald-100 rounded-full flex items-center justify-center mb-8 shadow-inner">
             <span className="text-5xl">🌾</span>
          </div>
          <h1 className="text-3xl font-black text-gray-900 mb-4 tracking-tight">
            {t('welcome_title')}
          </h1>
          <p className="text-gray-600 text-lg leading-relaxed">
            {t('welcome_subtitle')}
          </p>
          <div className="mt-8 pt-6 border-t border-gray-100 flex items-center justify-center space-x-2 text-sm font-medium text-emerald-700 bg-emerald-50 py-3 rounded-xl">
             <Database className="w-4 h-4"/> 
             <span>{t('data_source_notice')}</span>
          </div>
        </div>
      </div>
    );
  }

  // ─── Loading ─────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <div className="flex flex-col items-center space-y-6">
          <div className="relative w-16 h-16">
            <div className="absolute inset-0 border-4 border-emerald-100 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <span className="text-gray-600 font-medium text-lg animate-pulse">
            {t('gathering_insights')} {commodity}...
          </span>
        </div>
      </div>
    );
  }

  // ─── Error ───────────────────────────────────────────────────────────────────

  if (error) {
    return (
      <div className="max-w-2xl mx-auto mt-12">
        <div className="bg-red-50 border border-red-100 rounded-3xl p-8 text-center shadow-xl shadow-red-100/50">
          <div className="w-16 h-16 mx-auto bg-red-100 rounded-full flex items-center justify-center mb-6">
            <span className="text-3xl">⚠️</span>
          </div>
          <h3 className="text-2xl font-bold text-red-900 mb-3">
            {t('data_unavailable')}
          </h3>
          <p className="text-red-700 text-lg">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  // ─── Data display ────────────────────────────────────────────────────────────

  const trendUp = (data.trend_percent || 0) >= 0;
  const trendColor = trendUp ? "text-emerald-600" : "text-red-600";
  const trendBg = trendUp ? "bg-emerald-50 border-emerald-100" : "bg-red-50 border-red-100";
  const TrendIcon = trendUp ? TrendingUp : TrendingDown;

  const historyData = (data.history || []).map((h) => ({
    date: h.date,
    price: h.price,
    forecast: null,
  }));

  const forecastData = (data.forecast || []).map((f) => ({
    date: f.date,
    price: null,
    forecast: f.predicted_price ?? f.price,
  }));

  const chartData = [...historyData, ...forecastData];
  const separatorDate =
    historyData.length > 0 ? historyData[historyData.length - 1].date : null;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-2">
            <span className="px-3 py-1 bg-white border border-gray-200 rounded-full text-xs font-bold text-gray-500 uppercase tracking-widest shadow-sm">
              {t('live_analysis')}
            </span>
            <span className="px-3 py-1 bg-emerald-50 border border-emerald-100 rounded-full text-xs font-bold text-emerald-700 uppercase tracking-widest flex items-center">
              <Activity className="w-3 h-3 mr-1" /> {t('ai_active')}
            </span>
          </div>
          <h1 className="text-4xl font-black text-gray-900 tracking-tight">
            {commodity} <span className="text-gray-400 font-light px-2">|</span> {mandi}
          </h1>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Current Price */}
        <div className="bg-white rounded-3xl border border-gray-100 shadow-xl shadow-gray-200/40 p-6 hover:-translate-y-1 transition-transform duration-300">
          <div className="flex justify-between items-start mb-4">
            <p className="text-sm font-bold text-gray-500 uppercase tracking-widest">
              {t('current_market_price')}
            </p>
            <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
              <Database className="w-5 h-5" />
            </div>
          </div>
          <p className="text-4xl font-black text-gray-900 tracking-tight">
            ₹{((data.current_price ?? data.history?.[data.history.length - 1]?.price ?? 0)).toLocaleString("en-IN")}
          </p>
          <div className="flex items-center text-sm text-gray-500 mt-2 font-medium">
            <span>{t('per_quintal')}</span>
            <span className="mx-2 text-gray-300">/</span>
            <span className="text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">₹{(((data.current_price ?? data.history?.[data.history.length - 1]?.price ?? 0)) / 100).toFixed(2)} / kg</span>
          </div>
        </div>

        {/* 7-Day Trend */}
        <div className={`rounded-3xl border shadow-xl shadow-gray-200/40 p-6 hover:-translate-y-1 transition-transform duration-300 ${trendBg}`}>
          <div className="flex justify-between items-start mb-4">
            <p className={`text-sm font-bold uppercase tracking-widest ${trendColor}`}>
              {t('seven_day_trajectory')}
            </p>
            <div className={`p-2 rounded-lg bg-white/60 ${trendColor}`}>
              <TrendIcon className="w-5 h-5" />
            </div>
          </div>
          <p className={`text-4xl font-black tracking-tight ${trendColor}`}>
            {trendUp ? "+" : ""}{Math.abs(data.trend_percent || 0).toFixed(1)}%
          </p>
          <p className={`text-sm mt-2 font-medium ${trendColor} opacity-80`}>
            {trendUp ? t('trending_upwards') : t('trending_downwards')}
          </p>
        </div>

        {/* Total Records */}
        <div className="bg-gray-900 rounded-3xl border border-gray-800 shadow-xl shadow-gray-900/40 p-6 hover:-translate-y-1 transition-transform duration-300 relative overflow-hidden">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-white/5 rounded-full blur-2xl"></div>
          <div className="flex justify-between items-start mb-4 relative z-10">
            <p className="text-sm font-bold text-gray-400 uppercase tracking-widest">
              {t('data_confidence')}
            </p>
          </div>
          <p className="text-4xl font-black text-white tracking-tight relative z-10">
            {(data.total_records || 0).toLocaleString("en-IN")}
          </p>
          <p className="text-sm text-gray-400 mt-2 font-medium relative z-10">
            {t('historical_records_analyzed')}
          </p>
        </div>
      </div>

      {/* Chart */}
      {chartData.length > 0 && (
        <div className="bg-white rounded-3xl border border-gray-100 shadow-xl shadow-gray-200/40 p-6">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-lg font-bold text-gray-900 tracking-tight">
              {t('ai_price_projection')}
            </h3>
            <div className="flex items-center space-x-4 text-sm font-medium">
              <div className="flex items-center"><div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div> {t('historical')}</div>
              <div className="flex items-center"><div className="w-3 h-3 bg-emerald-500 rounded-full mr-2 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div> {t('forecast')}</div>
            </div>
          </div>
          
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12, fill: '#64748b', fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                  dy={10}
                  tickFormatter={(d) => {
                    const dt = new Date(d);
                    return dt.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
                  }}
                />
                <YAxis
                  tick={{ fontSize: 12, fill: '#64748b', fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                  dx={-10}
                  tickFormatter={(v) => `₹${v}`}
                />
                <Tooltip
                  contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)', padding: '16px' }}
                  itemStyle={{ fontWeight: 600 }}
                  labelStyle={{ fontWeight: 700, color: '#1e293b', marginBottom: '8px' }}
                  formatter={(value, name) => [
                    `₹${Number(value).toLocaleString("en-IN")}`,
                    name === "price" ? t('historical') : t('forecast'),
                  ]}
                  labelFormatter={(d) =>
                    new Date(d).toLocaleDateString("en-IN", { weekday: 'long', day: "numeric", month: "short", year: "numeric" })
                  }
                />
                {separatorDate && (
                  <ReferenceLine
                    x={separatorDate}
                    stroke="#94a3b8"
                    strokeDasharray="4 4"
                    label={{ value: "Today", position: "insideTopLeft", fill: "#64748b", fontSize: 12, fontWeight: 600 }}
                  />
                )}
                <Area
                  type="monotone"
                  dataKey="price"
                  stroke="#3b82f6"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorPrice)"
                  name="price"
                  connectNulls={false}
                />
                <Area
                  type="monotone"
                  dataKey="forecast"
                  stroke="#10b981"
                  strokeWidth={3}
                  strokeDasharray="4 4"
                  fillOpacity={1}
                  fill="url(#colorForecast)"
                  name="forecast"
                  connectNulls={false}
                  activeDot={{ r: 6, fill: '#10b981', stroke: '#fff', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Forecast Table */}
      {data.forecast && data.forecast.length > 0 && (
        <div className="bg-white rounded-3xl border border-gray-100 shadow-xl shadow-gray-200/40 p-6 overflow-hidden">
          <div className="mb-6">
            <h3 className="text-lg font-bold text-gray-900 tracking-tight">
              {data.horizon_days || horizon}-{t('forecast_matrix')}
            </h3>
            <p className="text-sm text-gray-500 mt-1">{t('forecast_subtitle')}</p>
          </div>
          
          <div className="overflow-x-auto -mx-6 px-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-gray-100">
                  <th className="text-left py-4 px-4 font-bold text-gray-400 uppercase tracking-wider text-xs">
                    {t('target_date')}
                  </th>
                  <th className="text-right py-4 px-4 font-bold text-gray-400 uppercase tracking-wider text-xs">
                    {t('predicted_price')}
                  </th>
                  <th className="text-right py-4 px-4 font-bold text-gray-400 uppercase tracking-wider text-xs">
                    {t('expected_range')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.forecast.map((f, i) => (
                  <tr
                    key={i}
                    className="border-b border-gray-50 hover:bg-gray-50 transition-colors group"
                  >
                    <td className="py-4 px-4 text-gray-900 font-semibold flex items-center">
                      <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center mr-3 group-hover:bg-emerald-100 group-hover:text-emerald-700 transition-colors">
                        {i + 1}
                      </div>
                      {new Date(f.date).toLocaleDateString(language === 'hi' ? 'hi-IN' : 'en-IN', {
                        weekday: 'short',
                        day: "numeric",
                        month: "short",
                      })}
                    </td>
                    <td className="py-4 px-4 text-right">
                      <div className="font-bold text-lg text-emerald-600">
                        ₹{Number(f.predicted_price ?? f.price ?? 0).toLocaleString("en-IN")}
                      </div>
                      <div className="text-xs text-gray-400 font-medium">₹{(Number(f.predicted_price ?? f.price ?? 0)/100).toFixed(2)}/kg</div>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <div className="font-semibold text-gray-600">
                        ₹{Number(f.lower_bound ?? f.lower ?? 0).toLocaleString("en-IN")} —{" "}
                        ₹{Number(f.upper_bound ?? f.upper ?? 0).toLocaleString("en-IN")}
                      </div>
                      <div className="text-xs text-gray-400">
                        {t('volatility_margin')}: ~{Math.round(((f.upper_bound ?? f.upper ?? 0) - (f.lower_bound ?? f.lower ?? 0)) / (f.predicted_price ?? f.price ?? 1) * 100)}%
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
