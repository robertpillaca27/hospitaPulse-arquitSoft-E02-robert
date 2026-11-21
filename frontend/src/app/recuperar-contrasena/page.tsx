import Link from "next/link";

export default function RecoverPasswordPage() {
  return (
    <main className="entry-page">
      <section className="entry-card">
        <Link className="entry-brand" href="/" aria-label="HospitaPulse, inicio">
          <span className="brand-mark"><span>+</span></span>
          <span className="brand-copy"><strong>hospita<span>pulse</span></strong><small>CLIMA ORGANIZACIONAL</small></span>
        </Link>
        <div className="entry-form">
          <div>
            <span className="panel-kicker">RECUPERACIÓN DE ACCESO</span>
            <h1>¿Olvidaste tu contraseña?</h1>
            <p>La recuperación automática por correo todavía no está habilitada.</p>
          </div>
          <p className="entry-recovery-note">
            Contacta al administrador del sistema para solicitar una contraseña temporal.
            En <strong>Usuarios y roles</strong>, el administrador puede restablecerla;
            se te pedirá cambiarla al iniciar sesión.
          </p>
          <Link className="personnel-primary-button recovery-back-button" href="/">Volver al inicio de sesión</Link>
        </div>
      </section>
    </main>
  );
}
