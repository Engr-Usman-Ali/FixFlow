// Content blocks of the public landing page. No technical details, only what the product does.
import { Link } from "react-router-dom";
import {
  BellRing, Building2, ClipboardCheck, ClipboardList, Gauge, ShieldCheck, Sparkles, UserCheck, Wrench,
} from "lucide-react";
import type { ReactNode } from "react";

const FEATURES: { icon: ReactNode; title: string; text: string }[] = [
  { icon: <ClipboardList size={20} />, title: "Report in a minute",
    text: "Describe the problem, say where it is and link the equipment. You get a request number straight away." },
  { icon: <Gauge size={20} />, title: "Priorities you can trust",
    text: "Employees flag urgency, managers confirm it, and work that runs past its target is marked overdue." },
  { icon: <Sparkles size={20} />, title: "Helpful suggestions",
    text: "Optional smart suggestions propose a category and priority from your description. You always make the call." },
  { icon: <UserCheck size={20} />, title: "Clear ownership",
    text: "Managers pick a technician. Every assignment and reassignment is recorded, so nobody guesses who has the job." },
  { icon: <Wrench size={20} />, title: "Repair records that last",
    text: "Diagnosis, parts used and completion notes stay with the request and with the equipment for next time." },
  { icon: <BellRing size={20} />, title: "Updates and reports",
    text: "Notifications keep everyone current. Managers see totals, technician workload and equipment that keeps breaking." },
  { icon: <Building2 size={20} />, title: "One workspace per company",
    text: "Each company gets its own private space, request numbers, categories and locations. Nobody sees another company's data." },
  { icon: <ShieldCheck size={20} />, title: "Access you control",
    text: "A System Administrator adds people, sets roles, resets passwords and can see an audit log of every important change." },
];

const STEPS = [
  { title: "Report", text: "An employee describes the problem and submits it." },
  { title: "Review and assign", text: "A manager confirms the priority and chooses a technician." },
  { title: "Repair and document", text: "The technician records the diagnosis, work done and the result." },
  { title: "Close and learn", text: "The manager signs it off. The history stays for reports and future repairs." },
];

const ROLES = [
  { role: "Employees", points: ["Report a problem in a few fields", "Follow progress without chasing anyone", "Get notified when it is fixed"] },
  { role: "Technicians", points: ["See only the jobs assigned to you", "Log diagnosis, actions and parts", "Submit completion details for sign-off"] },
  { role: "Managers", points: ["Review the queue and set priorities", "Assign and reassign technicians", "Keep equipment records and read reports"] },
  { role: "Administrators", points: ["Invite people with a company code", "Set roles and reset passwords", "Configure categories, locations and targets"] },
];

export function Features() {
  return (
    <section id="features" className="section">
      <div className="section-inner">
        <h2 className="section-title">Everything a repair needs, in one place</h2>
        <p className="section-lead">No more messages, spreadsheets and hallway requests. One record follows each job until it is done.</p>
        <div className="feature-grid">
          {FEATURES.map((f) => (
            <article key={f.title} className="feature">
              <span className="feature-icon">{f.icon}</span>
              <h3>{f.title}</h3>
              <p>{f.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export function HowItWorks() {
  return (
    <section id="how" className="section section-ink">
      <div className="section-inner">
        <h2 className="section-title">How a repair moves through FixFlow</h2>
        <ol className="steps">
          {STEPS.map((s, i) => (
            <li key={s.title}>
              <span className="step-num">{i + 1}</span>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

export function Roles() {
  return (
    <section id="roles" className="section">
      <div className="section-inner">
        <h2 className="section-title">Built for the people doing the work</h2>
        <div className="role-grid">
          {ROLES.map((r) => (
            <article key={r.role} className="role-card">
              <h3>{r.role}</h3>
              <ul>{r.points.map((p) => <li key={p}><ClipboardCheck size={16} />{p}</li>)}</ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export function CallToAction() {
  return (
    <section className="cta">
      <h2>Stop chasing repairs. Start closing them.</h2>
      <p>Register your company in a minute, then invite your team with a join code.</p>
      <div className="action-row center">
        <Link to="/register?mode=company" className="btn btn-signal btn-large">Register your company</Link>
        <Link to="/login" className="btn btn-outline-light btn-large">Sign in</Link>
      </div>
    </section>
  );
}
