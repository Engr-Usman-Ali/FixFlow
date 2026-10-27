import { Wrench } from "lucide-react";
import { Link } from "react-router-dom";

export default function Logo({ to = "/", light = false }: { to?: string; light?: boolean }) {
  return (
    <Link to={to} className={`logo ${light ? "logo-light" : ""}`} aria-label="FixFlow home">
      <span className="logo-mark"><Wrench size={16} strokeWidth={2.6} /></span>
      FixFlow
    </Link>
  );
}
