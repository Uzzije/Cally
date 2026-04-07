type WorkspacePageHeaderProps = {
  eyebrow: string
  title: string
  intro: string
}

export function WorkspacePageHeader({
  eyebrow,
  title,
  intro,
}: WorkspacePageHeaderProps) {
  return (
    <header className="workspace-header editorial-header">
      <div className="workspace-title-group">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="workspace-intro">{intro}</p>
      </div>
    </header>
  )
}
