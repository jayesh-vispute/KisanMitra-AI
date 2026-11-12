import { useState, useEffect } from "react";
import staticMetadata from "../data/static_metadata.json";
import { useSettings } from "../contexts/SettingsContext";
import { useTranslation } from "../locales/translations";

export default function Sidebar({ onSelectionChange }) {
  const { language } = useSettings();
  const { t } = useTranslation(language);

  // Default pre-selected values so data loads immediately on first open
  const [selectedState, setSelectedState] = useState("Maharashtra");
  const [selectedDistrict, setSelectedDistrict] = useState("Nashik");
  const [selectedMandi, setSelectedMandi] = useState("Nashik");
  const [selectedCommodity, setSelectedCommodity] = useState("Onion");
  const [horizon, setHorizon] = useState(7);

  // Derived Data Lists from Static Metadata
  const states = staticMetadata.states || [];
  const districts = selectedState ? (staticMetadata.districts[selectedState] || []) : [];
  const mandis = selectedDistrict ? (staticMetadata.mandis[selectedDistrict] || []) : [];
  const commodities = selectedMandi ? (staticMetadata.commodities[selectedMandi] || staticMetadata.default_commodities) : [];

  // Notify parent component on initial render
  useEffect(() => {
    onSelectionChange?.({
      state: "Maharashtra",
      district: "Nashik",
      mandi: "Nashik",
      commodity: "Onion",
      horizon: 7,
    });
  }, []);

  const handleStateChange = (e) => {
    const s = e.target.value;
    setSelectedState(s);
    setSelectedDistrict("");
    setSelectedMandi("");
    setSelectedCommodity("");
  };

  const handleDistrictChange = (e) => {
    const d = e.target.value;
    setSelectedDistrict(d);
    setSelectedMandi("");
    setSelectedCommodity("");
  };

  const handleMandiChange = (e) => {
    const m = e.target.value;
    setSelectedMandi(m);
    setSelectedCommodity("");
  };

  const handleCommodityChange = (e) => {
    const commodity = e.target.value;
    setSelectedCommodity(commodity);
    if (commodity && selectedMandi) {
      onSelectionChange?.({
        state: selectedState,
        district: selectedDistrict,
        mandi: selectedMandi,
        commodity,
        horizon,
      });
    }
  };

  const handleHorizonChange = (e) => {
    const h = parseInt(e.target.value, 10) || 7;
    setHorizon(h);
    if (selectedCommodity && selectedMandi) {
      onSelectionChange?.({
        state: selectedState,
        district: selectedDistrict,
        mandi: selectedMandi,
        commodity: selectedCommodity,
        horizon: h,
      });
    }
  };

  const selectClass =
    "w-full px-3 py-2.5 bg-white border border-green-200 rounded-lg text-sm " +
    "focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-green-400 " +
    "disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed " +
    "transition-colors font-medium";

  const labelClass = "block text-xs font-semibold text-green-800 mb-1.5 uppercase tracking-wide";

  return (
    <aside className="w-72 bg-gradient-to-b from-green-50 to-white border-r border-green-100 p-5 space-y-5 overflow-y-auto flex-shrink-0">
      <div className="flex items-center space-x-2 mb-2">
        <span className="text-xl">🌾</span>
        <h2 className="text-lg font-bold text-green-900">{t('market_selection')}</h2>
      </div>

      {/* State */}
      <div>
        <label className={labelClass}>{t('state_label')}</label>
        <select
          className={selectClass}
          value={selectedState}
          onChange={handleStateChange}
        >
          <option value="">{t('select_state')}</option>
          {states.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* District */}
      <div>
        <label className={labelClass}>{t('district_label')}</label>
        <select
          className={selectClass}
          value={selectedDistrict}
          onChange={handleDistrictChange}
          disabled={!selectedState}
        >
          <option value="">
            {!selectedState ? t('select_state_first') : t('select_district')}
          </option>
          {districts.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {/* Mandi */}
      <div>
        <label className={labelClass}>{t('mandi_label')}</label>
        <select
          className={selectClass}
          value={selectedMandi}
          onChange={handleMandiChange}
          disabled={!selectedDistrict}
        >
          <option value="">
            {!selectedDistrict ? t('select_district_first') : t('select_mandi')}
          </option>
          {mandis.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      {/* Commodity */}
      <div>
        <label className={labelClass}>{t('commodity_label')}</label>
        <select
          className={selectClass}
          value={selectedCommodity}
          onChange={handleCommodityChange}
          disabled={!selectedMandi}
        >
          <option value="">
            {!selectedMandi ? t('select_mandi_first') : t('select_commodity')}
          </option>
          {commodities.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* Horizon */}
      <div>
        <label className={labelClass}>{t('forecast_horizon')}</label>
        <input
          type="number"
          min={1}
          max={30}
          value={horizon}
          onChange={handleHorizonChange}
          className={selectClass}
        />
      </div>

      {/* Current Selection Summary */}
      {selectedCommodity && selectedMandi && (
        <div className="bg-green-100 border border-green-200 rounded-lg p-3 text-xs text-green-800 space-y-1">
          <p className="font-bold text-green-900">{t('active_selection')}</p>
          <p>📍 {selectedMandi}, {selectedDistrict || 'Nashik'}</p>
          <p>🌱 {selectedCommodity}</p>
          <p>📅 {horizon} {t('forecast_days_suffix')}</p>
        </div>
      )}
    </aside>
  );
}
