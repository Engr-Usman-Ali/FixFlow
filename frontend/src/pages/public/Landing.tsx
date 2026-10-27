import { Link } from "react-router-dom";
import { CallToAction, Features, HowItWorks, Roles } from "../../components/landing/Sections";
import TicketPreview from "../../components/landing/TicketPreview";
import Logo from "../../components/layout/Logo";
import { useAuth } from "../../context/AuthContext";

export default function Landing() {
  const { user } = useAuth();

  return (
    <div className="landing">
      <header className="l-nav">
        <Logo />
        <nav className="l-links" aria-label="Page sections">
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
          <a href="#roles">Who it is for</a>
        </nav>
        <div className="l-actions">
          {user ? (
            <Link to="/app" className="btn btn-primary">Open dashboard</Link>
          ) : (
            <>
              <Link to="/login" className="btn btn-ghost">Sign in</Link>
              <Link to="/register" className="btn btn-primary">Join or register</Link>
            </>
          )}
        </div>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <h1>Every repair, from first report to final sign-off.</h1>
          <p>
            FixFlow gives employees, technicians and managers one shared place to report problems,
            assign the work and see what has been fixed.
          </p>
          <div className="action-row">
            <Link to="/register?mode=company" className="btn btn-primary btn-large">Register your company</Link>
            <a href="#how" className="btn btn-secondary btn-large">See how it works</a>
          </div>
        </div>
        <TicketPreview />
      </section>

      <Features />
      <HowItWorks />
      <Roles />
      <CallToAction />

      <footer className="l-footer">
        <Logo />
        <span className="muted small">Maintenance and repair management, made simple.</span>
      </footer>
    </div>
  );
}
