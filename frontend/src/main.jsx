import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <main className="app-crash">
          <section className="form-shell">
            <span className="section-kicker">APPLICATION ERROR</span>
            <h1>The page could not continue.</h1>
            <p>{this.state.error.message || "An unexpected frontend error occurred."}</p>
            <button type="button" className="run-button" onClick={() => window.location.reload()}>
              Reload page
            </button>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
