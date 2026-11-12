import { useState, Component } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";
import VoiceAssistant from "./components/VoiceAssistant";

import Dashboard from "./pages/Dashboard";
import Forecast from "./pages/Forecast";
import Weather from "./pages/Weather";
import Alerts from "./pages/Alerts";
import CropHealth from "./pages/CropHealth";
import FarmerAdvisory from "./pages/FarmerAdvisory";

// ─── Error Boundary ──────────────────────────────────────────────────────────

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("[ErrorBoundary]", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-green-50 flex items-center justify-center p-8">
          <div className="bg-white rounded-2xl shadow-lg border border-green-200 p-10 max-w-md text-center">
            <div className="text-5xl mb-4">🌿</div>
            <h1 className="text-2xl font-bold text-green-900 mb-2">
              Something went wrong
            </h1>
            <p className="text-green-700 mb-6 text-sm">
              An unexpected error occurred. Please refresh the page to continue.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

import Landing from "./pages/Landing";

// ─── App Component ───────────────────────────────────────────────────────────

export default function App() {
  const [selection, setSelection] = useState({
    state: "Maharashtra",
    district: "Nashik",
    mandi: "Nashik",
    commodity: "Onion",
    horizon: 7,
  });

  const handleSelectionChange = (newSelection) => {
    setSelection((prev) => ({ ...prev, ...newSelection }));
  };

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          {/* Landing Page Route */}
          <Route path="/" element={<Landing />} />

          {/* Internal Application Routes */}
          <Route
            path="/*"
            element={
              <div className="min-h-screen bg-gray-50 flex flex-col">
                {/* Top Navbar */}
                <Navbar />

                {/* Body: Sidebar + Main */}
                <div className="flex flex-1 overflow-hidden">
                  <Sidebar onSelectionChange={handleSelectionChange} />

                  <main className="flex-1 overflow-y-auto p-6">
                    <Routes>
                      <Route
                        path="/dashboard"
                        element={<Dashboard selection={selection} />}
                      />
                      <Route
                        path="/forecast"
                        element={
                          <Forecast
                            commodity={selection.commodity}
                            mandi={selection.mandi}
                            horizon={selection.horizon}
                          />
                        }
                      />
                      <Route
                        path="/weather"
                        element={<Weather mandi={selection.mandi} />}
                      />
                      <Route
                        path="/alerts"
                        element={
                          <Alerts
                            commodity={selection.commodity}
                            mandi={selection.mandi}
                          />
                        }
                      />
                      <Route
                        path="/crop-health"
                        element={
                          <CropHealth
                            mandi={selection.mandi}
                            commodity={selection.commodity}
                          />
                        }
                      />
                      <Route
                        path="/farmer-advisory"
                        element={
                          <FarmerAdvisory
                            commodity={selection.commodity}
                            mandi={selection.mandi}
                          />
                        }
                      />
                    </Routes>
                  </main>
                </div>

                {/* Floating Chat */}
                <VoiceAssistant
                  commodity={selection.commodity}
                  mandi={selection.mandi}
                />
              </div>
            }
          />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
