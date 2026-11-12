import { Component } from "react";

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("KisanMitra render error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          height: "100vh", gap: "16px", 
          fontFamily: "sans-serif",
          background: "#f0fdf4"
        }}>
          <div style={{ fontSize: "56px" }}>🌾</div>
          <h2 style={{ color: "#166534", margin: 0, 
                       fontSize: "20px" }}>
            KisanMitra is updating market data
          </h2>
          <p style={{ color: "#6b7280", textAlign: "center",
                      maxWidth: "380px", lineHeight: "1.6" }}>
            The server is refreshing live prices. 
            This usually takes a few seconds.
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{
              padding: "10px 28px", background: "#16a34a",
              color: "white", border: "none", 
              borderRadius: "8px", cursor: "pointer",
              fontSize: "14px", fontWeight: "500"
            }}
          >
            Refresh Page
          </button>
          {this.state.error && (
            <details style={{ fontSize: "11px", 
                             color: "#9ca3af",
                             maxWidth: "400px" }}>
              <summary>Technical details</summary>
              <pre style={{ whiteSpace: "pre-wrap" }}>
                {this.state.error.toString()}
              </pre>
            </details>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
