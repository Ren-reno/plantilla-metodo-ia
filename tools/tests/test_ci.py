"""Prueba el bloque real de validación del CI con Bash y repos temporales."""
import os
import shutil
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

from test_validar import RepoTemporal

RAIZ = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")


@unittest.skipUnless(BASH, "se necesita Bash para ejecutar el bloque del CI")
class TestIntegracionCI(unittest.TestCase):
    def setUp(self):
        self.repo = RepoTemporal(self)
        workflow = (RAIZ / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        paso = workflow.split("      - name: Validar diseño y plan\n", 1)[1]
        bloque = paso.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0]
        self.script = textwrap.dedent(bloque)

    def correr_ci(self):
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        entorno["PATH"] = str(Path(sys.executable).parent) + os.pathsep + entorno.get("PATH", "")
        return subprocess.run([BASH, "--noprofile", "--norc", "-e", "-c", self.script],
                              cwd=str(self.repo.dir), env=entorno, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")

    def test_plantilla_vacia_avisa_y_no_falla(self):
        self.repo.poner("docs/plan/tareas/.gitkeep", "")
        r = self.correr_ci()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("::notice::Todavía no hay docs/plan/backlog.md", r.stdout)
        self.assertIn("Las pruebas de tools/ se ejecutan igualmente", r.stdout)
        self.assertNotIn("Validación exitosa", r.stdout)

    def test_diseno_sin_plan_todavia_no_valida_cobertura(self):
        self.repo.poner("docs/requisitos/contexto.md", "# Diseño antes de planificar\n")
        r = self.correr_ci()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("::notice::Todavía no hay docs/plan/backlog.md", r.stdout)

    def test_plan_valido_ejecuta_el_validador(self):
        self.repo.poblar_ejemplo()
        r = self.correr_ci()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Validación exitosa", r.stdout)
        self.assertNotIn("::notice::", r.stdout)

    def test_plan_incoherente_detiene_el_ci(self):
        self.repo.poblar_ejemplo()
        self.repo.poner("docs/requisitos/RF-099-nuevo.md", "# RF-099 · Sin cobertura\nAporta a: C1\n")
        r = self.correr_ci()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("RF-099", r.stdout)
        self.assertIn("Validación fallida", r.stdout)

    def test_backlog_danado_no_se_omite(self):
        self.repo.poner("docs/plan/backlog.md", "Esto no es un backlog válido\n")
        r = self.correr_ci()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("Error al leer", r.stdout)
        self.assertNotIn("::notice::", r.stdout)

    def test_error_del_validador_no_se_oculta(self):
        self.repo.poner("docs/plan/backlog.md", "plan presente\n")
        self.repo.poner("tools/validar.py", "raise RuntimeError('fallo inesperado')\n")
        r = self.correr_ci()
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("fallo inesperado", r.stderr)

    def test_sin_herramienta_conserva_el_aviso_original(self):
        (self.repo.dir / "tools/validar.py").unlink()
        r = self.correr_ci()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("::notice::Todavía no existe tools/validar.py", r.stdout)


if __name__ == "__main__":
    unittest.main()
