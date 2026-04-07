export function AuthErrorPage() {
  return (
    <main className="workspace-page centered-shell">
      <section className="paper-panel status-panel">
        <p className="eyebrow">Authentication</p>
        <h1>We couldn&apos;t complete sign in</h1>
        <p>
          The Google login flow was interrupted or rejected. Return to the login
          screen and try again.
        </p>
        <a className="primary-link-button button-md" href="/">
          Return to login
        </a>
      </section>
    </main>
  )
}
