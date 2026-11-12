import { createContext, useContext, useState, useEffect } from 'react';

const SettingsContext = createContext();

export const useSettings = () => useContext(SettingsContext);

export const SettingsProvider = ({ children }) => {
  const [language, setLanguage] = useState(() => localStorage.getItem('kisan_lang') || 'en');
  const [mode, setMode] = useState(() => localStorage.getItem('kisan_mode') || 'professional');
  const [fontSize, setFontSize] = useState(() => localStorage.getItem('kisan_font') || 'normal');
  const [highContrast, setHighContrast] = useState(() => localStorage.getItem('kisan_contrast') === 'true');

  useEffect(() => {
    localStorage.setItem('kisan_lang', language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem('kisan_mode', mode);
  }, [mode]);

  useEffect(() => {
    localStorage.setItem('kisan_font', fontSize);
    if (fontSize === 'large') {
      document.documentElement.classList.add('text-lg');
    } else {
      document.documentElement.classList.remove('text-lg');
    }
  }, [fontSize]);

  useEffect(() => {
    localStorage.setItem('kisan_contrast', highContrast);
    if (highContrast) {
      document.documentElement.classList.add('high-contrast');
    } else {
      document.documentElement.classList.remove('high-contrast');
    }
  }, [highContrast]);

  return (
    <SettingsContext.Provider value={{
      language, setLanguage,
      mode, setMode,
      fontSize, setFontSize,
      highContrast, setHighContrast
    }}>
      <div className={highContrast ? 'grayscale contrast-125' : ''}>
        {children}
      </div>
    </SettingsContext.Provider>
  );
};
