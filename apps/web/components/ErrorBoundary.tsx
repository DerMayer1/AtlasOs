'use client'

import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="min-h-screen bg-black flex items-center justify-center">
          <div className="max-w-sm w-full px-6 text-center">
            <p className="text-zinc-500 text-xs uppercase tracking-widest mb-3">Error</p>
            <h2 className="text-white text-lg font-medium mb-2">Something went wrong</h2>
            <p className="text-zinc-500 text-sm mb-6">
              {this.state.error?.message ?? 'An unexpected error occurred.'}
            </p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="text-sm text-zinc-400 hover:text-white underline underline-offset-4 transition"
            >
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
