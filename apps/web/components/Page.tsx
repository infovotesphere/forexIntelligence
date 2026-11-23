import { AppShell } from "./AppShell";

export function Page({ title, description, active, children }: {
  title: string; description: string; active: string; children?: React.ReactNode;
}) {
  return (
    <AppShell active={active}>
      <main className="content">
        <div className="heading-row"><div><h1>{title}</h1><p>{description}</p></div></div>
        {children}
      </main>
    </AppShell>
  );
}
