import { getGoogleLoginUrl } from '../api/authClient'


export function LoginPage() {
  return (
    <main className="login-shell">
      <div className="login-atmosphere login-atmosphere-left" />
      <div className="login-atmosphere login-atmosphere-right" />

      <section className="login-stage">
        <div className="brand-stack">
          <div className="brand-mark" aria-hidden="true">
            <span className="brand-book">
              <span />
              <span />
            </span>
          </div>
          <p className="brand-name">Cal Assistant</p>
          <p className="brand-tagline">Calendar workspace</p>
        </div>

        <section className="login-card" aria-label="Sign in">
          <div className="login-copy">
            <h1>Welcome back</h1>
            <p>
              Sign in to access your calendar workspace and connected Google account.
            </p>
          </div>

          <a className="google-button button-lg" href={getGoogleLoginUrl()}>
            <span className="google-mark" aria-hidden="true">
              G
            </span>
            <span>Sign in with Google</span>
          </a>

          <div className="login-divider" />

          <div className="login-meta">
            <p>Google sign-in is required for secure calendar access.</p>
          </div>
        </section>

        <footer className="login-footer">
          <a href="mailto:support@calassistant.local">Privacy Policy</a>
          <a href="mailto:support@calassistant.local">Terms of Service</a>
          <a href="mailto:support@calassistant.local">Support</a>
        </footer>
      </section>
    </main>
  )
}
