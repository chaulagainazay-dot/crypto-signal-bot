import { Component, type ReactNode } from 'react'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State { return { error } }

  render() {
    if (this.state.error) {
      return this.props.fallback ?? (
        <div style={{ padding: 24, textAlign: 'center', color: '#FF3D57' }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>⚠️</div>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>Something went wrong</div>
          <div style={{ color: '#606060', fontSize: 12 }}>{this.state.error.message}</div>
          <button
            onClick={() => this.setState({ error: null })}
            style={{ marginTop: 16, padding: '10px 20px', background: '#F7931A', border: 'none', borderRadius: 10, color: '#000', fontWeight: 700, cursor: 'pointer' }}
          >
            Try Again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
