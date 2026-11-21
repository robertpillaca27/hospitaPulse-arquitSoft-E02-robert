"use client";

import { useParams } from "next/navigation";

import InstitutionalWorkspace from "@/components/institutional-workspace";
import type { InstitutionalModule } from "@/lib/api/institutional";

const modules: InstitutionalModule[] = [
  "sugerencias",
  "planes-mejora",
  "reconocimientos",
  "organigrama",
  "eventos",
  "comunicaciones",
  "auditoria",
];

export default function InstitutionalModulePage() {
  const params = useParams<{ module: string }>();
  const module = modules.find((item) => item === params.module);
  if (!module) {
    return <main className="institutional-page"><section className="institutional-card"><h1>Módulo no disponible</h1><a href="/">Volver al resumen</a></section></main>;
  }
  return <InstitutionalWorkspace module={module} />;
}
