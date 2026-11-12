import { useEffect, useState } from 'react';
import { getAlerts } from '../utils/api';
import AlertBanner from '../components/AlertBanner';
import { useSettings } from '../contexts/SettingsContext';
import { useTranslation } from '../locales/translations';

const Alerts = ({ commodity, mandi }) => {
  const { language } = useSettings();
  const { t } = useTranslation(language);

  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = async () => {
      setLoading(true);
      try {
        const data = await getAlerts();
        setAlerts(data.alerts);
      } catch (error) {
        console.error("Alerts error:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchAlerts();
  }, [commodity, mandi]);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('alerts_notifications')}</h1>
          <p className="text-gray-500 mt-1">{language === 'hi' ? 'AI द्वारा पहचानी गई बाजार एवं मौसम की स्थिति' : 'Abnormal price surges & weather condition updates'}</p>
        </div>
        <div className="bg-primary/10 text-primary px-4 py-2 rounded-xl font-bold">
          {alerts.length} {t('nav_alerts')}
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1,2,3].map(i => <div key={i} className="h-24 bg-gray-50 animate-pulse rounded-xl border border-gray-100"></div>)}
        </div>
      ) : alerts.length > 0 ? (
        <div className="space-y-4">
          {alerts.map((alert, i) => <AlertBanner key={i} alert={alert} />)}
        </div>
      ) : (
        <div className="bg-white rounded-xl p-12 text-center border border-gray-100 shadow-sm flex flex-col items-center justify-center">
          <div className="text-6xl mb-4 opacity-50">🌿</div>
          <h3 className="text-xl text-gray-900 font-bold mb-2">
            {language === 'hi' ? 'सभी बाजार भाव स्थिर हैं' : 'All prices are stable'}
          </h3>
          <p className="text-gray-500 max-w-sm">{t('no_active_alerts')}</p>
        </div>
      )}
    </div>
  );
};

export default Alerts;
