import { Component } from "react";

// Catches render/runtime errors in its subtree and shows a recovery card instead of a
// blank page. Used both at the top level (catches anything, incl. the header) and around
// the routed content keyed by pathname (so navigating away clears the error).
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Unhandled UI error:", error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;
    const err = this.state.error;
    return (
      <div className="container">
        <div className="card error-card">
          <h1>Something went wrong</h1>
          <p className="muted">
            An unexpected error interrupted this page. Nothing you were viewing is lost —
            try reloading, or head back to the home page.
          </p>
          <div className="error-actions">
            <button className="btn" onClick={() => window.location.reload()}>
              Reload
            </button>
            <a className="btn btn-ghost-dark" href="/">
              Go to home
            </a>
          </div>
          <details className="error-details">
            <summary>Technical details</summary>
            <pre>{String(err.stack || err.message || err)}</pre>
          </details>
        </div>
      </div>
    );
  }
}
