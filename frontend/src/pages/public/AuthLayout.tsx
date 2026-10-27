import { ReactNode } from "react";
import Logo from "../../components/layout/Logo";

/** Two-panel layout shared by the sign-in and sign-up pages. */
export default function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="auth-page">
      <aside className="auth-aside">
        <Logo light />
        <div>
          <h2>Every repair, from first report to final sign-off.</h2>
          <p>Report problems, assign the right technician and see exactly where each job stands.</p>
        </div>
      </aside>
      <main className="auth-main">
        <div className="auth-card">
          <h1>{title}</h1>
          <p className="muted">{subtitle}</p>
          {children}
        </div>
      </main>
    </div>
  );
}
