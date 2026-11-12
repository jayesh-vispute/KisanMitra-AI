import { useState, useEffect } from "react";
import { useSettings } from "../contexts/SettingsContext";
import { useTranslation } from "../locales/translations";

const MANDI_COORDS = {
  Nashik:    { lat: 20.0059, lon: 73.7898 },
  Pune:      { lat: 18.5204, lon: 73.8567 },
  Kolhapur:  { lat: 16.7050, lon: 74.2433 },
  Mumbai:    { lat: 19.0760, lon: 72.8777 },
  Delhi:     { lat: 28.6139, lon: 77.2090 },
  Bangalore: { lat: 12.9716, lon: 77.5946 },
  Chennai:   { lat: 13.0827, lon: 80.2707 },
  Hyderabad: { lat: 17.3850, lon: 78.4867 },
};

const WEATHER_CODES = {
  0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy",
  3: "Overcast", 45: "Foggy", 48: "Icy fog",
  51: "Light drizzle", 61: "Light rain", 63: "Moderate rain",
  65: "Heavy rain", 80: "Rain showers", 95: "Thunderstorm",
};

export default function Weather({ mandi = "Nashik" }) {
  const { language } = useSettings();
  const { t } = useTranslation(language);

  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const coords = MANDI_COORDS[mandi] || MANDI_COORDS["Nashik"];
    setLoading(true);
    setError(null);

    fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${coords.lat}&longitude=${coords.lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Asia%2FKolkata&forecast_days=7`
    )
      .then((res) => {
        if (!res.ok) throw new Error("Weather fetch failed");
        return res.json();
      })
      .then((data) => {
        setWeather(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [mandi]);

  const getFarmingAdvisory = (precipSums) => {
    if (!precipSums) return "";
    const next3Days = precipSums.slice(0, 3).reduce((a, b) => a + b, 0);
    if (language === 'hi') {
      if (next3Days > 10) return "🌧️ भारी बारिश की संभावना — कटाई टालने पर विचार करें";
      if (next3Days < 2) return "☀️ सूखा मौसम — फसलों की सिंचाई सुनिश्चित करें";
      return "🌤️ सामान्य मौसम — खेत के काम के लिए उपयुक्त";
    }
    if (language === 'mr') {
      if (next3Days > 10) return "🌧️ मुसळधार पावसाची शक्यता — काढणी पुढे ढकला";
      if (next3Days < 2) return "☀️ कोरडे हवामान — पिकांना पाणी द्या";
      return "🌤️ अनुकूल हवामान — शेतातील कामासाठी योग्य";
    }
    if (next3Days > 10)
      return "🌧️ Heavy rainfall expected — consider delaying harvest";
    if (next3Days < 2)
      return "☀️ Dry conditions — ensure irrigation for your crops";
    return "🌤️ Moderate conditions — suitable for fieldwork";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full animate-spin" />
        <span className="ml-3 text-gray-500">{t('weather_forecast')} for {mandi}...</span>
      </div>
    );
  }

  if (error || !weather) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
        {t('data_unavailable')} for {mandi}.
      </div>
    );
  }

  const current = weather.current;
  const daily = weather.daily;
  const advisory = getFarmingAdvisory(daily?.precipitation_sum);

  return (
    <div className="space-y-4">
      <div className="bg-gradient-to-br from-green-50 to-blue-50 rounded-xl p-5 border border-green-100">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-xl font-semibold text-gray-800">{mandi} {t('mandi_label')}</h2>
            <p className="text-sm text-gray-500">
              {WEATHER_CODES[current?.weather_code] || "Current conditions"}
            </p>
          </div>
          <div className="text-right">
            <p className="text-4xl font-bold text-green-700">
              {current?.temperature_2m ?? "--"}°C
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mt-3">
          <div className="bg-white rounded-lg p-3 text-center shadow-sm">
            <p className="text-xs text-gray-400">{t('humidity')}</p>
            <p className="text-lg font-semibold text-blue-600">
              {current?.relative_humidity_2m ?? "--"}%
            </p>
          </div>
          <div className="bg-white rounded-lg p-3 text-center shadow-sm">
            <p className="text-xs text-gray-400">{t('wind_speed')}</p>
            <p className="text-lg font-semibold text-blue-600">
              {current?.wind_speed_10m ?? "--"} km/h
            </p>
          </div>
          <div className="bg-white rounded-lg p-3 text-center shadow-sm">
            <p className="text-xs text-gray-400">{t('precipitation')}</p>
            <p className="text-lg font-semibold text-blue-600">
              {current?.precipitation ?? "--"} mm
            </p>
          </div>
        </div>
      </div>

      {advisory && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-sm font-medium text-amber-800">{advisory}</p>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-600 mb-3">{t('three_day_outlook')}</h3>
        <div className="space-y-2">
          {daily?.time?.map((date, i) => (
            <div key={date} className="flex items-center justify-between text-sm">
              <span className="text-gray-500 w-24">
                {new Date(date).toLocaleDateString(language === 'hi' ? 'hi-IN' : 'en-IN', { weekday: "short", month: "short", day: "numeric" })}
              </span>
              <div className="flex-1 mx-3">
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-400 to-green-400 rounded-full"
                    style={{
                      width: `${Math.min(100, ((daily.precipitation_sum[i] || 0) / 20) * 100)}%`,
                      minWidth: "4px"
                    }}
                  />
                </div>
              </div>
              <span className="text-blue-600 font-medium w-8 text-right">
                {daily?.temperature_2m_max?.[i] ?? "--"}°
              </span>
              <span className="text-gray-400 w-8 text-right">
                {daily?.temperature_2m_min?.[i] ?? "--"}°
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
