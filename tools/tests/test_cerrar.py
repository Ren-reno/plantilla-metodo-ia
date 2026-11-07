"""Pruebas de tools/cerrar.py. Solo usan la biblioteca estándar (y git, que el método ya exige).

Correr desde la raíz del repo:
    python -m unittest discover -s tools/tests -v
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

AQUI = Path(__file__).resolve().parent
TOOLS = AQUI.parent
sys.path.insert(0, str(TOOLS))
import bundle as bd  # noqa: E402
import cerrar as ce  # noqa: E402
import init_plan as ip  # noqa: E402

PLAN = (AQUI / "fixtures" / "PLAN-ejemplo.md").read_text(encoding="utf-8")
DISENO = (AQUI / "fixtures" / "DISENO-ejemplo.md").read_text(encoding="utf-8")
PLANTILLA = TOOLS.parent / "docs" / "plantillas" / "reporte.md"
REPARTO_PLAN = dict(ip.Plan(PLAN).analizar().reparto())  # backlog, cobertura y tarjetas reales del ejemplo
MODELO = "# Modelo\n\n## Actividad\n- a1\n- a2\n\n## Otra\n- o1\n"  # «Actividad» ocupa las líneas 3 a 6


# ---- ayudas ---------------------------------------------------------------
def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=prueba", "-c", "user.email=prueba@example.com", *args],
                   cwd=str(cwd), check=True, capture_output=True)


def reporte(tid="T-001", hecho="Se dejó el esqueleto andando.", supuestos="ninguno", decisiones="ninguna",
            probar="Correr los tests.\n\n- Verificado: los tests pasan en local\n- No verificado: el CI de GitHub",
            commit="feat: esqueleto andante"):
    return (f"# Reporte {tid}\n\n## Hecho\n\n{hecho}\n\n## Supuestos\n\n{supuestos}\n\n## Decisiones tomadas\n\n"
            f"{decisiones}\n\n## Pendientes\n\nNada.\n\n## Cómo probar\n\n{probar}\n\n"
            f"## Mensaje de commit sugerido\n\n`{commit}`\n")


def adr(num="0001", estado="aceptada", titulo="Una decisión"):
    return f"# ADR-{num} · {titulo}\n\nEstado: {estado} · Motivo: x · Afecta: y\n"


def hay(lista, fragmento):
    return any(fragmento in x for x in lista)


def sin_seccion(texto, titulo):
    """Quita una sección «## titulo» del reporte, con su contenido."""
    ini = texto.index(f"## {titulo}\n")
    sig = texto.find("\n## ", ini + 1)
    return texto[:ini] + (texto[sig + 1:] if sig != -1 else "")


class Repo:
    """Un repo de git temporal con el mundo del ejemplo «Biblioteca de barrio»."""

    def __init__(self, test, con_mundo=True):
        self.dir = Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, self.dir, True)
        git(self.dir, "init", "-q")
        if con_mundo:
            self.mundo()

    def poner(self, rel, texto="", como_bytes=None):
        ruta = self.dir / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(como_bytes if como_bytes is not None else texto.encode("utf-8"))

    def leer(self, rel):
        return (self.dir / rel).read_text(encoding="utf-8")

    def mundo(self):
        self.poner(".gitignore", "bundles/\n__pycache__/\n" + ("tools/\n" if (self.dir / "tools").is_dir() else ""))
        self.poner("docs/00-LEEME-IA.md", "# Reglas\n")
        self.poner("docs/modelo.md", MODELO)
        self.poner("docs/decisiones/0001-usar-una-base-de-datos-relacional.md", adr("0001", "aceptada", "Usar una base"))
        self.poner("docs/decisiones/0002-interfaz-web-sencilla-sin-app-movil.md", adr("0002", "aceptada", "Interfaz web"))
        for rel in (ip.REL_BACKLOG, ip.REL_COBERTURA, "docs/plan/tareas/T-001.md", "docs/plan/tareas/T-002.md",
                    "docs/plan/tareas/T-003.md"):
            self.poner(rel, REPARTO_PLAN[rel])
        self.commit("base")

    def commit(self, mensaje="x"):
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-qm", mensaje, "--allow-empty")

    def trabajo(self, archivos, mensaje="feat: trabajo de la tarea"):
        for rel, texto in archivos.items():
            self.poner(rel, texto)
        self.commit(mensaje)

    def trabajo_de_t001(self):
        self.trabajo({"src/app.py": "print('hola')\n", "tests/test_humo.py": "def test_humo(): pass\n",
                      ".github/workflows/ci.yml": "name: ci\n"})

    def cerrar(self, tarea="T-001", texto=None, **kw):
        return ce.planear(self.dir, tarea, reporte(tarea) if texto is None else texto, **kw)

    def aplicar(self, c):
        ce._aplicar(self.dir, c.escrituras, c.borrar)
        return c

    def estado(self):
        return ce.leer_estado(self.leer(ce.REL_ESTADO))[1]

    def staged(self):
        return subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=str(self.dir), capture_output=True,
                              text=True, encoding="utf-8").stdout.split()


class RepoCli(Repo):
    """Como Repo, pero con las herramientas copiadas, para probar la línea de comandos de verdad."""

    def __init__(self, test, con_mundo=True):
        super().__init__(test, con_mundo=False)
        (self.dir / "tools").mkdir()
        for nombre in ("init_diseno.py", "init_plan.py", "bundle.py", "cerrar.py", "validar.py"):
            shutil.copy(TOOLS / nombre, self.dir / "tools" / nombre)
        self.home = Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, self.home, True)
        if con_mundo:
            self.mundo()

    def correr(self, herramienta, *args, env=None):
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8", HOME=str(self.home), USERPROFILE=str(self.home))
        entorno.update(env or {})
        return subprocess.run([sys.executable, str(self.dir / "tools" / herramienta), *args], cwd=str(self.dir),
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno)

    def cerrar_cli(self, *args, env=None):
        return self.correr("cerrar.py", *args, env=env)

    def archivos(self):
        return sorted(p.relative_to(self.dir).as_posix() for p in self.dir.rglob("*")
                      if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts)


# ---- el reporte --------------------------------------------------------------
class LecturaDelReporte(unittest.TestCase):
    def test_un_reporte_correcto_no_trae_errores_ni_avisos(self):
        r = ce.Reporte(reporte())
        self.assertEqual((r.errores, r.avisos), ([], []))
        self.assertEqual((r.id, r.commit, r.decisiones), ("T-001", "feat: esqueleto andante", []))
        self.assertEqual(sorted(r.secciones), sorted(ce.SECCIONES))

    @unittest.skipUnless(PLANTILLA.is_file(), "no está docs/plantillas/reporte.md")
    def test_la_plantilla_de_reporte_cumple_el_formato(self):
        r = ce.Reporte(PLANTILLA.read_text(encoding="utf-8"))
        self.assertEqual(r.errores, [], "la plantilla y el analizador deben estar de acuerdo")
        self.assertTrue(hay([m for _, m in r.avisos], "sin llenar"))
        self.assertEqual(r.decisiones, [], "una decisión sin llenar no se convierte en propuesta")

    def test_cada_error_del_reporte_se_dice(self):
        base = reporte()
        invertido = base.replace("## Hecho\n\nSe dejó el esqueleto andando.\n\n", "").replace(
            "## Supuestos\n", "## Supuestos\n", 1)
        invertido = invertido.replace("## Pendientes", "## Hecho\n\nSe dejó el esqueleto andando.\n\n## Pendientes")
        casos = [
            ("vacío", "", "el reporte está vacío"),
            ("falta una sección", sin_seccion(base, "Supuestos"), "falta la sección «## Supuestos»"),
            ("título distinto", base.replace("## Hecho", "## Lo hecho"), "sección desconocida «## Lo hecho»; ¿quisiste decir «Hecho»?"),
            ("fuera de orden", invertido, "las secciones van en este orden"),
            ("sección repetida", base + "\n## Pendientes\n\nOtra vez.\n", "la sección «Pendientes» está repetida"),
            ("sección vacía", base.replace("## Supuestos\n\nninguno\n", "## Supuestos\n"), "la sección «Supuestos» está vacía"),
            ("sección con solo un comentario",
             base.replace("## Supuestos\n\nninguno\n", "## Supuestos\n\n<!-- nada -->\n"), "la sección «Supuestos» está vacía"),
        ]
        for nombre, texto, mensaje in casos:
            with self.subTest(nombre):
                r = ce.Reporte(texto)
                self.assertTrue(hay([m for _, m in r.errores], mensaje), f"salió: {r.errores}")

    def test_el_error_de_orden_o_repeticion_trae_su_linea(self):
        base = reporte()
        r = ce.Reporte(base + "\n## Pendientes\n\nOtra vez.\n")
        n = [x for x, m in r.errores if "repetida" in m][0]
        self.assertEqual(base.count("\n") + 2, n)

    def test_cada_aviso_del_reporte(self):
        base = reporte()
        casos = [
            ("sin «Verificado»", base.replace("- Verificado: los tests pasan en local\n", ""), "no trae «Verificado:»"),
            ("sin «No verificado»", base.replace("- No verificado: el CI de GitHub", ""), "no trae «No verificado:»"),
            ("sin ninguna de las dos", base.replace("- Verificado: los tests pasan en local\n- No verificado: el CI de GitHub", "Nada."),
             "«Verificado:» ni «No verificado:»"),
            ("commit que no es convencional", reporte(commit="arreglé cosas"), "no es un commit convencional"),
            ("sin título", base.replace("# Reporte T-001\n", ""), "falta el título «# Reporte T-007»"),
            ("título raro", base.replace("# Reporte T-001", "# Mi reporte"), "el título debería ser"),
            ("campo sin llenar", base.replace("Nada.", "«qué quedó fuera»"), "sin llenar"),
        ]
        for nombre, texto, mensaje in casos:
            with self.subTest(nombre):
                r = ce.Reporte(texto)
                self.assertEqual(r.errores, [], r.errores)
                self.assertTrue(hay([m for _, m in r.avisos], mensaje), f"salió: {r.avisos}")

    def test_negritas_y_variantes_de_verificado_se_aceptan(self):
        for probar in ("- **Verificado:** sí\n- **No verificado:** el CI", "* Verificado: sí\n* No verificado: el CI",
                       "Verificado: sí\nNo verificado: el CI", "- **Verificado**: sí\n- **No verificado**: el CI"):
            with self.subTest(probar):
                self.assertEqual(ce.Reporte(reporte(probar=probar)).avisos, [])

    def test_commits_convencionales_validos(self):
        for mensaje in ("feat: algo", "fix(auth): algo", "docs: algo", "test: algo", "refactor!: algo", "chore: x", "ci: x"):
            with self.subTest(mensaje):
                self.assertEqual(ce.Reporte(reporte(commit=mensaje)).avisos, [])
        for mensaje in ("Feat: algo", "feat:algo", "feature: algo", "feat algo"):
            with self.subTest(mensaje):
                self.assertTrue(hay([m for _, m in ce.Reporte(reporte(commit=mensaje)).avisos], "no es un commit convencional"))

    def test_decisiones_ninguna(self):
        for texto in ("ninguna", "Ninguna.", "Ninguno", "  ninguna  "):
            with self.subTest(texto):
                self.assertEqual(ce.Reporte(reporte(decisiones=texto)).decisiones, [])

    def test_decisiones_con_motivo_y_la_que_afecta_a_otras_tareas(self):
        r = ce.Reporte(reporte(decisiones=(
            "- Usar Flask · Motivo: es lo más simple. Afecta a otras tareas\n"
            "- Los tests viven en tests/ · Motivo: es la convención del repo\n"
            "- Sin motivo explícito. afecta a otras tareas\n"
            "1. Una numerada · Motivo: sí")))
        self.assertEqual(r.decisiones, [
            {"titulo": "Usar Flask", "motivo": "es lo más simple", "afecta": True},
            {"titulo": "Los tests viven en tests/", "motivo": "es la convención del repo", "afecta": False},
            {"titulo": "Sin motivo explícito", "motivo": "", "afecta": True},
            {"titulo": "Una numerada", "motivo": "sí", "afecta": False}])

    def test_una_decision_puede_seguir_en_la_linea_siguiente(self):
        r = ce.Reporte(reporte(decisiones="- Usar Flask · Motivo: es simple\n  y conocido. Afecta a otras tareas\nTexto suelto."))
        self.assertEqual(r.decisiones, [{"titulo": "Usar Flask", "motivo": "es simple y conocido", "afecta": True}])

    def test_el_separador_de_lineas_de_adr_no_se_cuela_en_los_titulos(self):
        r = ce.Reporte(reporte(decisiones="- Usar A · B · Motivo: por C · D"))
        self.assertEqual(r.decisiones[0]["titulo"], "Usar A - B")
        self.assertEqual(r.decisiones[0]["motivo"], "por C - D")

    def test_decisiones_sin_vinetas_se_leen_como_una_y_se_avisa(self):
        r = ce.Reporte(reporte(decisiones="Elegí Flask porque es simple. Afecta a otras tareas"))
        self.assertEqual(len(r.decisiones), 1)
        self.assertTrue(r.decisiones[0]["afecta"])
        self.assertTrue(hay([m for _, m in r.avisos], "no encontré viñetas"))

    def test_una_decision_sin_llenar_no_cuenta(self):
        r = ce.Reporte(reporte(decisiones="- «decisión» · Motivo: «por qué»"))
        self.assertEqual(r.decisiones, [])
        self.assertTrue(hay([m for _, m in r.avisos], "sin llenar"))

    def test_el_titulo_con_otro_numero_se_lee_para_compararlo(self):
        self.assertEqual(ce.Reporte(reporte("T-009")).id, "T-009")
        self.assertEqual(ce.Reporte(reporte("REF-02")).id, "REF-02")


# ---- git, «Tocar:» y secciones ------------------------------------------------------------
class CambiosDeGit(unittest.TestCase):
    def test_en_tocar(self):
        items = bd.Tarjeta("# T-001 · x\nEstado: pendiente · Depende de: — · Cubre: C1\nLeer (solo esto): a\n"
                           "Tocar: src/libros/* · docs/modelo.md (solo la sección Actividad) · src/config/\n").tocar
        for ruta, esperado in (("src/libros/a.py", True), ("src/libros/sub/b.py", True), ("docs/modelo.md", True),
                               ("src/config/settings.py", True), ("src/otro/a.py", False), ("src/libros", False),
                               ("docs/otro.md", False), ("tests/x.py", False)):
            with self.subTest(ruta):
                self.assertEqual(ce.en_tocar(ruta, items), esperado)

    def test_los_cambios_son_los_del_ultimo_commit_y_desde_permite_mas(self):
        r = Repo(self)
        r.trabajo({"a.txt": "1\n"}, "uno")
        r.trabajo({"b.txt": "2\n"}, "dos")
        ultimo = ce.leer_cambios(r.dir, "HEAD~1")
        self.assertEqual(ultimo.archivos, [("A", "b.txt")])
        self.assertEqual(len(ultimo.commit), 7)
        self.assertEqual(ce.leer_cambios(r.dir, "HEAD~2").archivos, [("A", "a.txt"), ("A", "b.txt")])

    def test_estados_agregado_modificado_y_borrado(self):
        r = Repo(self)
        r.trabajo({"a.txt": "1\n", "b.txt": "1\n"}, "base2")
        (r.dir / "b.txt").unlink()
        r.trabajo({"a.txt": "2\n", "c.txt": "1\n"}, "cambio")
        self.assertEqual(ce.leer_cambios(r.dir, "HEAD~1").archivos, [("M", "a.txt"), ("D", "b.txt"), ("A", "c.txt")])

    def test_un_renombrado_cuenta_como_borrado_mas_agregado(self):
        r = Repo(self)
        r.trabajo({"a.txt": "contenido largo para que git lo detecte como renombrado\n" * 5}, "base2")
        (r.dir / "a.txt").rename(r.dir / "b.txt")
        r.commit("renombro")
        self.assertEqual(ce.leer_cambios(r.dir, "HEAD~1").archivos, [("D", "a.txt"), ("A", "b.txt")])

    def test_los_nombres_con_acentos_y_espacios_llegan_enteros(self):
        r = Repo(self)
        r.trabajo({"docs/canción ñandú.md": "x\n"})
        self.assertEqual(ce.leer_cambios(r.dir, "HEAD~1").archivos, [("A", "docs/canción ñandú.md")])

    def test_los_cambios_sin_guardar_se_cuentan_menos_el_propio_reporte(self):
        r = Repo(self)
        r.trabajo({"a.txt": "1\n"})
        r.poner("sucio.txt", "x\n")
        r.poner("reporte.md", "r\n")
        self.assertEqual(ce.leer_cambios(r.dir, "HEAD~1").sucios, 2)
        self.assertEqual(ce.leer_cambios(r.dir, "HEAD~1", ignorar=["reporte.md"]).sucios, 1)

    def test_los_errores_de_git_se_explican(self):
        r = Repo(self, con_mundo=False)
        with self.assertRaisesRegex(bd.GitError, "todavía no tiene commits"):
            ce.leer_cambios(r.dir, "HEAD~1")
        r.poner("a.txt", "x\n")
        r.commit("unico")
        with self.assertRaisesRegex(bd.GitError, "primer commit del repo"):
            ce.leer_cambios(r.dir, "HEAD~1")
        with self.assertRaisesRegex(bd.GitError, "no encuentro el commit «nada»"):
            ce.leer_cambios(r.dir, "nada")
        with self.assertRaisesRegex(bd.GitError, "no es un commit"):
            ce.leer_cambios(r.dir, "--output=algo")

    def test_nunca_se_corre_un_comando_que_modifique_git(self):
        r = Repo(self)
        for comando in (("add", "-A"), ("rm", "x"), ("commit", "-m", "x"), ("checkout", "."), ("reset", "--hard"),
                        ("clean", "-f"), ("restore", "."), ("push",), ("stash",)):
            with self.subTest(comando):
                with self.assertRaisesRegex(bd.GitError, "nunca modifica git"):
                    ce._git(r.dir, *comando)
        self.assertEqual(ce._git(r.dir, "status", "--porcelain").returncode, 0)

    def test_secciones_los_cambios_dentro_y_fuera(self):
        r = Repo(self)
        base = "# Modelo\n\n## Actividad\n- a1\n- a2\n\n## Otra\n- o1\n"
        casos = [
            ("dentro", base.replace("- a1", "- A1"), []),
            ("fuera", base.replace("- o1", "- O1"), [(8, 8)]),
            ("dentro y fuera", base.replace("- a1", "- A1").replace("- o1", "- O1"), [(8, 8)]),
            ("una línea nueva al final de la sección", base.replace("- a2\n", "- a2\n- a3\n"), []),
            ("borrar una línea de la sección", base.replace("- a2\n", ""), []),
            ("borrar la última línea del archivo", base.replace("- o1\n", ""), [(7, 7)]),
        ]
        for nombre, nuevo, esperado in casos:
            with self.subTest(nombre):
                r.poner("docs/modelo.md", base)
                r.commit("base")
                r.poner("docs/modelo.md", nuevo)
                r.commit("cambio")
                self.assertEqual(ce.cambios_fuera_de_seccion(r.dir, "HEAD~1", "docs/modelo.md", "Actividad"), esperado)

    def test_una_seccion_que_no_existe_se_dice_con_none(self):
        r = Repo(self)
        r.trabajo({"docs/modelo.md": MODELO + "- x\n"})
        self.assertIsNone(ce.cambios_fuera_de_seccion(r.dir, "HEAD~1", "docs/modelo.md", "Inexistente"))
        self.assertEqual(ce.cambios_fuera_de_seccion(r.dir, "HEAD~1", "docs/modelo.md", "otra"), [])  # sin mayúsculas


# ---- banderas y avisos -----------------------------------------------------------------------
class Banderas(unittest.TestCase):
    def test_un_cierre_limpio_no_trae_banderas_ni_avisos(self):
        r = Repo(self)
        r.trabajo_de_t001()
        c = r.cerrar(llm="Claude")  # un cierre limpio declara quien hizo la tarea: sin --llm hay aviso
        self.assertEqual((c.codigo, c.negativas, c.errores, c.banderas, c.avisos), (0, [], [], [], []))
        self.assertEqual(c.filas["T-001"]["notas"], "")

    def test_archivos_fuera_de_tocar(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.trabajo({"extra.txt": "x\n", "src/app.py": "print('hola 2')\n", "docs/plan/tareas/T-002.md": "tocada\n"})
        c = r.cerrar(desde="HEAD~2")
        self.assertTrue(hay(c.banderas, "archivos fuera de «Tocar:» (2): docs/plan/tareas/T-002.md, extra.txt"))
        self.assertEqual(c.filas["T-001"]["notas"], "fuera de Tocar: 2")

    def test_archivo_de_dependencias_con_y_sin_pista(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.trabajo({"src/requirements.txt": "flask\n", "package.json": "{}\n"})
        c = r.cerrar()
        self.assertTrue(hay(c.banderas, "archivo de dependencias tocado: package.json, src/requirements.txt."))
        self.assertTrue(hay(c.banderas, "«Decisiones tomadas» no dice nada"))
        self.assertIn("dependencias", c.filas["T-001"]["notas"])
        c = r.cerrar(texto=reporte(decisiones="- Se agrega flask · Motivo: es el framework"))
        self.assertFalse(hay(c.banderas, "no dice nada"))

    def test_cambios_en_contratos(self):
        r = Repo(self)
        r.trabajo({"docs/contratos/api.md": "x\n"})
        c = r.cerrar()
        self.assertTrue(hay(c.banderas, "cambios en contratos: docs/contratos/api.md"))

    def test_tests_que_ya_existian_son_un_aviso_y_con_reintento_un_error(self):
        r = Repo(self)
        r.trabajo({"tests/test_humo.py": "def test_humo(): pass\n"}, "tests de antes")
        r.trabajo({"tests/test_humo.py": "def test_humo(): assert 1\n", "tests/test_nuevo.py": "x\n", "src/app.py": "x\n"})
        c = r.cerrar()
        self.assertEqual((c.codigo, c.negativas), (0, []))
        self.assertTrue(hay(c.avisos, "cambiaron tests que ya existían: tests/test_humo.py."))
        self.assertFalse(hay(c.avisos, "test_nuevo"), "un test nuevo no es un test modificado")
        c = r.cerrar(reintento=True)
        self.assertEqual(c.codigo, 1)
        self.assertTrue(hay(c.negativas, "con --reintento, un test que ya existía no puede cambiar: tests/test_humo.py"))
        self.assertEqual((c.escrituras, c.borrar), ([], []))

    def test_borrar_un_test_tambien_cuenta_como_modificarlo(self):
        r = Repo(self)
        r.trabajo({"tests/test_humo.py": "x\n"}, "tests de antes")
        (r.dir / "tests/test_humo.py").unlink()
        r.commit("borro")
        self.assertTrue(hay(r.cerrar().avisos, "cambiaron tests que ya existían: tests/test_humo.py"))

    def test_una_tarjeta_de_refactor_no_puede_tocar_tests(self):
        r = Repo(self)
        r.poner("docs/plan/tareas/REF-01.md", "# REF-01 · Ordenar\nEstado: pendiente · Tamaño: S · Depende de: — · Cubre: —\n"
                "Objetivo: x\nLeer (solo esto): docs/00-LEEME-IA.md\nTocar: src/prestamos/*\n")
        r.commit("tarjeta REF")
        r.trabajo({"src/prestamos/a.py": "x\n", "tests/prestamos/test_nuevo.py": "x\n"})
        c = r.cerrar("REF-01")
        self.assertEqual(c.codigo, 1)
        self.assertTrue(hay(c.negativas, "una tarjeta de refactor no puede tocar tests"))
        r.trabajo({"src/prestamos/b.py": "x\n"})  # el último commit solo toca código
        c = r.cerrar("REF-01")
        self.assertEqual((c.codigo, c.negativas), (0, []))
        self.assertEqual(c.filas["REF-01"]["estado"], "en revisión")

    def test_solo_la_seccion_x_en_un_documento_markdown(self):
        r = Repo(self)
        r.poner("docs/plan/tareas/T-001.md", REPARTO_PLAN["docs/plan/tareas/T-001.md"].replace(
            "docs/00-LEEME-IA.md (solo Convenciones y Comandos)", "docs/modelo.md (solo la sección Actividad)"))
        r.commit("tarjeta")
        r.trabajo({"docs/modelo.md": MODELO.replace("- a1", "- A1").replace("- o1", "- O1"), "src/app.py": "x\n"})
        c = r.cerrar()
        self.assertTrue(hay(c.banderas, "docs/modelo.md cambió fuera de la sección «Actividad» (líneas 8)"))
        self.assertIn("cambio fuera de sección", c.filas["T-001"]["notas"])
        r.trabajo({"docs/modelo.md": MODELO})  # vuelve a la base
        r.trabajo({"docs/modelo.md": MODELO.replace("- a1", "- A1")})
        self.assertFalse(hay(r.cerrar().banderas, "fuera de la sección"))
        r.trabajo({"docs/modelo.md": MODELO})
        r.trabajo({"docs/modelo.md": MODELO.replace("## Actividad", "## Otro nombre")})
        self.assertTrue(hay(r.cerrar().avisos, "no encontré la sección «Actividad» en docs/modelo.md"))

    def test_una_nota_que_no_se_puede_comprobar_se_avisa_para_revisarla_a_mano(self):
        r = Repo(self)
        r.trabajo({"docs/00-LEEME-IA.md": "# Reglas\n\nConvenciones nuevas\n", "src/app.py": "x\n"})
        c = r.cerrar()  # la tarjeta real de T-001 dice «docs/00-LEEME-IA.md (solo Convenciones y Comandos)»
        self.assertTrue(hay(c.avisos, "revisa a mano docs/00-LEEME-IA.md: la tarjeta dice «solo Convenciones y Comandos»"))

    def test_decisiones_que_afectan_a_otras_tareas_son_bandera_y_propuesta(self):
        r = Repo(self)
        r.trabajo_de_t001()
        c = r.cerrar(texto=reporte(decisiones="- Usar Flask · Motivo: es simple. Afecta a otras tareas\n- Algo local · Motivo: x"))
        self.assertEqual(len(c.banderas), 1)
        self.assertTrue(hay(c.banderas, "decisión que afecta a otras tareas: Usar Flask (se propone como ADR)"))
        self.assertEqual(c.adrs, ["docs/decisiones/0003-usar-flask.md"])
        self.assertEqual(c.filas["T-001"]["notas"], "decisiones que afectan a otras tareas: 1")

    def test_sin_cambios_y_con_cambios_sin_guardar_se_avisa(self):
        r = Repo(self)
        r.trabajo_de_t001()
        self.assertTrue(hay(r.cerrar(desde="HEAD").avisos, "no hay cambios entre HEAD y HEAD"))
        r.poner("pendiente.txt", "x\n")
        self.assertTrue(hay(r.cerrar().avisos, "1 archivo(s) con cambios sin guardar"))

    def test_los_errores_de_git_salen_con_2_y_sin_escribir_nada(self):
        r = Repo(self)
        for desde in ("nada", "--output=x"):
            c = r.cerrar(desde=desde)
            self.assertEqual(c.codigo, 2)
            self.assertEqual((c.escrituras, c.borrar), ([], []))


# ---- la guía de tres líneas de ESTADO.md -------------------------------------------------------
class GuiaDeEstado(unittest.TestCase):
    """Responde «¿y ahora qué?» sin reconstruir la conversación (H-01), sin otro archivo (H-24)."""

    def test_tras_el_cierre_provisorio_apunta_al_CI_y_al_cierre_definitivo(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.aplicar(r.cerrar())
        texto = r.leer(ce.REL_ESTADO)
        self.assertIn("- **Etapa:** 4. Código", texto)
        self.assertIn("cerrar.py T-001 --hecha", texto)
        self.assertIn("- **Tu decisión:** ninguna", texto)

    def test_tras_cerrar_del_todo_apunta_a_la_siguiente_tarea_desbloqueada(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.aplicar(r.cerrar())
        r.aplicar(ce.planear(r.dir, "T-001", hecha=True))
        texto = r.leer(ce.REL_ESTADO)
        self.assertIn("bundle.py T-002", texto)

    def test_una_tarea_desbloqueada_sin_tarjeta_manda_al_chat_de_hito(self):
        r = Repo(self)
        (r.dir / "docs/plan/tareas/T-002.md").unlink()
        r.trabajo_de_t001()
        r.aplicar(r.cerrar())
        r.aplicar(ce.planear(r.dir, "T-001", hecha=True))
        self.assertIn("no tiene tarjeta", r.leer(ce.REL_ESTADO))

    def test_el_parche_1_del_modo_estricto_apunta_al_parche_2(self):
        r = Repo(self)
        r.poner("docs/plan/tareas/T-001.md",
                REPARTO_PLAN["docs/plan/tareas/T-001.md"].replace("Objetivo:", "Modo: estricto\nObjetivo:"))
        r.trabajo({"tests/test_humo.py": "def test_humo(): pass\n"}, "test: parche 1")
        r.aplicar(r.cerrar(parcial=True))
        self.assertIn("bundle.py T-001 --parche2", r.leer(ce.REL_ESTADO))

    def test_una_decision_en_propuesta_se_nombra_porque_bloquea_el_bundle(self):
        r = Repo(self)
        r.poner("docs/decisiones/0002-interfaz-web-sencilla-sin-app-movil.md",
                adr("0002", "propuesta", "Interfaz web"))
        r.trabajo_de_t001()
        r.aplicar(r.cerrar())
        texto = r.leer(ce.REL_ESTADO)
        self.assertIn("ADR-0002", texto)
        self.assertIn("bundle.py se niega", texto)

    def test_la_guia_no_rompe_la_lectura_del_estado(self):
        orden, filas = ["T-001"], {"T-001": ce.fila_nueva()}
        guia = ["- **Etapa:** 4. Código", "- **Siguiente:** «python tools/bundle.py T-002»",
                "- **Tu decisión:** ninguna"]
        texto = ce.escribir_estado("x", orden, filas, guia)
        self.assertEqual(ce.leer_estado(texto), (orden, filas))
        self.assertIn("**Siguiente:**", texto)
        self.assertNotIn("|", "\n".join(guia), "una guía con «|» la leería como fila de la tabla")


# ---- ESTADO.md y los estados ------------------------------------------------------------------
class EstadoDelPlan(unittest.TestCase):
    def test_se_escribe_y_se_lee_de_vuelta(self):
        orden = ["T-001", "T-002", "REF-01"]
        filas = {"T-001": {"estado": "hecha", "llm": "Claude", "commit": "abc1234", "notas": "dependencias"},
                 "T-002": ce.fila_nueva(), "REF-01": {"estado": "parcial", "llm": "", "commit": "", "notas": "x"}}
        texto = ce.escribir_estado("Mi app", orden, filas)
        self.assertEqual(ce.leer_estado(texto), (orden, filas))
        self.assertIn("# Estado del plan — Mi app", texto)
        self.assertIn("Avance: 1 de 2 tareas hechas.", texto)  # las REF no cuentan en el avance
        self.assertIn("| T-002 | pendiente | — | — | — |", texto)

    def test_el_avance_en_singular(self):
        self.assertIn("Avance: 0 de 1 tarea hechas.", ce.escribir_estado("x", ["T-001"], {"T-001": ce.fila_nueva()}))

    def test_las_barras_no_rompen_la_tabla(self):
        f = ce.fila_nueva()
        f["llm"], f["notas"] = "a|b", "uno\ndos | tres"
        texto = ce.escribir_estado("x", ["T-001"], {"T-001": f})
        self.assertIn("| T-001 | pendiente | a/b | — | uno dos / tres |", texto)
        self.assertEqual(ce.leer_estado(texto)[1]["T-001"]["notas"], "uno dos / tres")

    def test_un_estado_ilegible_se_dice_con_su_linea(self):
        cab = "| Tarea | Estado | LLM | Commit | Notas |\n|---|---|---|---|---|\n"
        casos = [("sin tabla", "# Estado\n", "no encuentro la tabla"),
                 ("cabecera distinta", "| Tarea | Estado |\n|---|---|\n", "la cabecera debe ser"),
                 ("columnas", cab + "| T-001 | hecha |\n", "la fila debe tener 5 columnas"),
                 ("estado inválido", cab + "| T-001 | casi | — | — | — |\n", "el estado «casi» no es válido"),
                 ("no es una tarea", cab + "| X-1 | hecha | — | — | — |\n", "«X-1» no es una tarea"),
                 ("repetida", cab + "| T-001 | hecha | — | — | — |\n| T-001 | hecha | — | — | — |\n", "T-001 está repetida")]
        for nombre, texto, mensaje in casos:
            with self.subTest(nombre):
                with self.assertRaisesRegex(ValueError, mensaje):
                    ce.leer_estado(texto)

    def test_los_seis_estados_de_la_memoria_se_leen(self):
        cab = "| Tarea | Estado | LLM | Commit | Notas |\n|---|---|---|---|---|\n"
        filas = "".join(f"| T-00{i} | {e} | — | — | — |\n" for i, e in enumerate(ce.ESTADOS, 1))
        self.assertEqual(len(ce.leer_estado(cab + filas)[0]), 6)

    def test_el_primer_cierre_crea_el_estado_con_todo_el_backlog(self):
        r = Repo(self)
        r.trabajo_de_t001()
        c = r.aplicar(r.cerrar(llm="Claude"))
        filas = r.estado()
        self.assertEqual(list(filas), ["T-001", "T-002", "T-003", "T-004", "T-005"])
        self.assertEqual(filas["T-001"]["estado"], "en revisión")
        self.assertEqual((filas["T-001"]["llm"], len(filas["T-001"]["commit"])), ("Claude", 7))
        self.assertTrue(all(filas[t]["estado"] == "pendiente" for t in ("T-002", "T-003", "T-004", "T-005")))
        self.assertIn("# Estado del plan — Biblioteca de barrio", r.leer(ce.REL_ESTADO))
        self.assertIn("Avance: 0 de 5 tareas hechas.", r.leer(ce.REL_ESTADO))

    def test_cerrar_otra_tarea_conserva_lo_de_las_demas(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.aplicar(r.cerrar(llm="Claude"))
        r.trabajo({"src/libros/a.py": "x\n"})
        r.aplicar(r.cerrar("T-002", llm="Otro"))
        filas = r.estado()
        self.assertEqual((filas["T-001"]["estado"], filas["T-001"]["llm"]), ("en revisión", "Claude"))
        self.assertEqual((filas["T-002"]["estado"], filas["T-002"]["llm"]), ("en revisión", "Otro"))

    def test_cerrar_dos_veces_pide_reintento(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.aplicar(r.cerrar())
        c = r.cerrar()
        self.assertEqual(c.codigo, 1)
        self.assertTrue(hay(c.negativas, "ya está «en revisión». Si es un segundo intento"))
        self.assertTrue(hay(c.negativas, f"ya existe {ce.REL_REPORTES}/T-001.md"))
        c = r.cerrar(reintento=True, llm="Otro")
        self.assertEqual((c.codigo, c.negativas), (0, []))
        r.aplicar(c)
        self.assertEqual(r.estado()["T-001"]["llm"], "Otro")

    def test_un_reintento_conserva_el_llm_si_no_se_repite(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.aplicar(r.cerrar(llm="Claude"))
        r.aplicar(r.cerrar(reintento=True))
        self.assertEqual(r.estado()["T-001"]["llm"], "Claude")

    def test_una_tarea_hecha_no_se_cierra_de_nuevo(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.aplicar(r.cerrar())
        r.aplicar(ce.planear(r.dir, "T-001", hecha=True))
        c = r.cerrar(reintento=True)  # sin tarjeta: no hay nada que cerrar
        self.assertEqual(c.codigo, 2)
        self.assertTrue(hay(c.negativas, "Si la tarea ya está hecha no hay nada que cerrar"))
        r.poner("docs/plan/tareas/T-001.md", REPARTO_PLAN["docs/plan/tareas/T-001.md"])  # y si la tarjeta reapareciera
        c = r.cerrar(reintento=True)
        self.assertEqual(c.codigo, 1)
        self.assertTrue(hay(c.negativas, "ya está «hecha»"))

    def test_el_estado_tambien_se_puede_pedir_con_minusculas(self):
        r = Repo(self)
        r.trabajo_de_t001()
        self.assertEqual(r.cerrar("t-001").codigo, 0)

    def test_modo_estricto_parche_1_queda_parcial_y_el_parche_2_en_revision(self):
        r = Repo(self)
        r.trabajo({"src/prestamos/__init__.py": "x\n", "tests/prestamos/test_p.py": "x\n"}, "test: parche 1")
        c = r.cerrar("T-003", texto=reporte("T-003"), parcial=True)
        self.assertEqual((c.codigo, c.negativas), (0, []))
        self.assertEqual(c.rel_reporte, f"{ce.REL_REPORTES}/T-003-parche1.md")
        self.assertEqual((c.filas["T-003"]["estado"], c.filas["T-003"]["notas"]), ("parcial", "parche 1 de 2"))
        r.aplicar(c)
        self.assertTrue((r.dir / "docs/plan/tareas/T-003.md").is_file(), "la tarjeta sigue: aún falta el parche 2")
        c = r.cerrar("T-003", texto=reporte("T-003"), parcial=True)
        self.assertTrue(hay(c.negativas, "ya está «parcial»"))
        r.trabajo({"src/prestamos/__init__.py": "y\n"}, "feat: parche 2")
        c = r.cerrar("T-003", texto=reporte("T-003"))
        self.assertEqual((c.codigo, c.negativas, c.rel_reporte), (0, [], f"{ce.REL_REPORTES}/T-003.md"))
        self.assertEqual(c.filas["T-003"]["estado"], "en revisión")

    def test_parcial_solo_sirve_en_modo_estricto(self):
        r = Repo(self)
        r.trabajo_de_t001()
        c = r.cerrar(parcial=True)
        self.assertEqual(c.codigo, 1)
        self.assertTrue(hay(c.negativas, "--parcial solo sirve con una tarjeta de «Modo: estricto»"))

    def test_las_tareas_que_ya_no_estan_en_el_backlog_y_las_ref_se_conservan(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.aplicar(r.cerrar())
        viejo = ce.leer_estado(r.leer(ce.REL_ESTADO))
        orden, filas = viejo[0] + ["T-099"], dict(viejo[1], **{"T-099": dict(ce.fila_nueva(), estado="hecha")})
        r.poner(ce.REL_ESTADO, ce.escribir_estado("x", orden, filas))
        r.poner("docs/plan/tareas/REF-01.md", "# REF-01 · Ordenar\nEstado: pendiente · Tamaño: S · Depende de: — · Cubre: —\n"
                "Objetivo: x\nLeer (solo esto): docs/00-LEEME-IA.md\nTocar: src/*\n")
        r.commit("ref")
        r.trabajo({"src/otro.py": "x\n"})
        r.aplicar(r.cerrar("REF-01"))
        filas = r.estado()
        self.assertEqual(list(filas)[-2:], ["T-099", "REF-01"])
        self.assertIn("ya no está en el backlog", filas["T-099"]["notas"])
        self.assertEqual((filas["T-099"]["estado"], filas["REF-01"]["estado"]), ("hecha", "en revisión"))
        self.assertEqual(filas["T-001"]["estado"], "en revisión")

    def test_problemas_del_mundo_se_explican(self):
        r = Repo(self)
        r.trabajo_de_t001()
        self.assertEqual(r.cerrar("hola").codigo, 2)
        c = r.cerrar("T-007")
        self.assertEqual(c.codigo, 2)
        self.assertTrue(hay(c.negativas, "no existe la tarjeta docs/plan/tareas/T-007.md"))
        r.poner("docs/plan/tareas/T-009.md", REPARTO_PLAN["docs/plan/tareas/T-001.md"].replace("T-001", "T-009"))
        c = r.cerrar("T-009", texto=reporte("T-009"))
        self.assertEqual(c.codigo, 1)
        self.assertTrue(hay(c.negativas, "T-009 no está en docs/plan/backlog.md"))
        r.poner(ce.REL_ESTADO, "esto no es un estado\n")
        c = r.cerrar()
        self.assertEqual(c.codigo, 2)
        self.assertTrue(hay(c.negativas, "Lo escribe solo cerrar.py"))
        (r.dir / ip.REL_BACKLOG).unlink()
        self.assertTrue(hay(r.cerrar().negativas, "no existe docs/plan/backlog.md"))

    def test_un_reporte_de_otra_tarea_se_rechaza(self):
        r = Repo(self)
        r.trabajo_de_t001()
        c = r.cerrar(texto=reporte("T-002"))
        self.assertEqual(c.codigo, 1)
        self.assertTrue(hay([m for _, m in c.errores], "el reporte es de T-002, pero estás cerrando T-001"))

    def test_un_reporte_con_errores_no_escribe_nada(self):
        r = Repo(self)
        r.trabajo_de_t001()
        c = r.cerrar(texto=sin_seccion(reporte(), "Supuestos"))
        self.assertEqual((c.codigo, c.escrituras, c.borrar), (1, [], []))


# ---- la recepción definitiva ------------------------------------------------------------------------
class RecepcionDefinitiva(unittest.TestCase):
    def cerrada(self, tarea="T-001"):
        r = Repo(self)
        if tarea == "T-001":
            r.trabajo_de_t001()
        else:
            r.trabajo({"src/libros/a.py": "x\n"})
        r.aplicar(r.cerrar(tarea))
        r.commit("cierre provisorio")
        return r

    def test_pasa_a_hecha_borra_la_tarjeta_y_lista_lo_desbloqueado(self):
        r = self.cerrada()
        c = ce.planear(r.dir, "T-001", hecha=True)
        self.assertEqual((c.codigo, c.negativas, c.modo), (0, [], "hecha"))
        self.assertEqual(c.borrar, ["docs/plan/tareas/T-001.md"])
        self.assertEqual(c.desbloqueadas, [("T-002", True)])
        r.aplicar(c)
        self.assertFalse((r.dir / "docs/plan/tareas/T-001.md").exists())
        self.assertEqual(r.estado()["T-001"]["estado"], "hecha")
        self.assertIn("Avance: 1 de 5 tareas hechas.", r.leer(ce.REL_ESTADO))

    def test_lo_desbloqueado_distingue_las_tareas_con_y_sin_tarjeta(self):
        r = self.cerrada()
        r.aplicar(ce.planear(r.dir, "T-001", hecha=True))
        r.commit("T-001 hecha")
        r.trabajo({"src/libros/a.py": "x\n"})
        r.aplicar(r.cerrar("T-002"))
        c = ce.planear(r.dir, "T-002", hecha=True)
        self.assertEqual(sorted(c.desbloqueadas), [("T-003", True), ("T-005", False)])  # T-005 es de la ola 2: sin tarjeta

    def test_una_tarea_con_varias_dependencias_espera_a_todas(self):
        r = Repo(self)
        r.poner(ip.REL_BACKLOG, REPARTO_PLAN[ip.REL_BACKLOG].replace(
            "Depende de: T-003 · Cubre: C2 (3), RF-003", "Depende de: T-003, T-005 · Cubre: C2 (3), RF-003"))
        r.commit("backlog con dos dependencias")
        r.trabajo({"src/prestamos/a.py": "x\n"})
        r.aplicar(r.cerrar("T-003"))
        self.assertEqual(ce.planear(r.dir, "T-003", hecha=True).desbloqueadas, [], "T-004 aún espera a T-005")

    def test_la_borradura_queda_sin_preparar_y_nada_entra_al_indice_de_git(self):
        r = self.cerrada()
        r.aplicar(ce.planear(r.dir, "T-001", hecha=True))
        estado = subprocess.run(["git", "status", "--porcelain"], cwd=str(r.dir), capture_output=True, text=True,
                                encoding="utf-8").stdout
        self.assertIn(" D docs/plan/tareas/T-001.md", estado, "borrado normal, sin «git rm»")
        self.assertNotIn("D  docs/plan/tareas/T-001.md", estado)
        self.assertEqual(r.staged(), [], "cerrar.py nunca prepara nada en git")

    def test_despues_de_hecha_bundle_ve_la_dependencia_como_hecha(self):
        r = self.cerrada()
        r.poner("docs/requisitos/RF-001-registrar-libro.md", "# RF-001\n")
        r.poner("docs/00-LEEME-IA.md", "# Reglas\n")
        before = bd.armar(r.dir, "T-002", home=r.dir / "sin-home")
        self.assertEqual(before.codigo, 1)
        self.assertTrue(hay(before.negativas, "T-001 no está hecha"))
        self.assertTrue(hay(before.negativas, "python tools/cerrar.py T-001 --hecha"))
        r.aplicar(ce.planear(r.dir, "T-001", hecha=True))
        despues = bd.armar(r.dir, "T-002", home=r.dir / "sin-home")
        self.assertEqual((despues.codigo, despues.negativas), (0, []))
        self.assertEqual(despues.notas, ["T-001 está hecha (su tarjeta ya no existe)"])

    def test_solo_una_tarea_en_revision_puede_pasar_a_hecha(self):
        r = Repo(self)
        for tarea, esperado in (("T-002", "primero ciérrala con su reporte"),):
            c = ce.planear(r.dir, tarea, hecha=True)
            self.assertEqual(c.codigo, 1)
            self.assertTrue(hay(c.negativas, f"{tarea} está «pendiente»: {esperado}"))
        r.trabajo({"src/prestamos/__init__.py": "x\n", "tests/prestamos/test_p.py": "x\n"})
        r.aplicar(r.cerrar("T-003", texto=reporte("T-003"), parcial=True))
        c = ce.planear(r.dir, "T-003", hecha=True)
        self.assertTrue(hay(c.negativas, "T-003 está «parcial»: falta el parche 2 (bundle.py T-003 --parche2)"))

    def test_una_tarea_ya_hecha_no_pasa_otra_vez(self):
        r = self.cerrada()
        r.aplicar(ce.planear(r.dir, "T-001", hecha=True))
        c = ce.planear(r.dir, "T-001", hecha=True)
        self.assertEqual(c.codigo, 1)
        self.assertTrue(hay(c.negativas, "T-001 está «hecha»: ya está hecha"))

    def test_si_la_tarjeta_ya_se_habia_borrado_a_mano_sigue_con_un_aviso(self):
        r = self.cerrada()
        (r.dir / "docs/plan/tareas/T-001.md").unlink()
        c = ce.planear(r.dir, "T-001", hecha=True)
        self.assertEqual((c.codigo, c.borrar), (0, []))
        self.assertTrue(hay(c.avisos, "ya no existe (¿la borraste a mano?)"))

    def test_el_indice_se_regenera_con_las_decisiones_que_aceptaste(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.aplicar(r.cerrar(texto=reporte(decisiones="- Usar Flask · Motivo: es simple. Afecta a otras tareas")))
        self.assertIn("| propuesta |", r.leer(ce.REL_INDICE))
        r.poner("docs/decisiones/0003-usar-flask.md", r.leer("docs/decisiones/0003-usar-flask.md").replace(
            "Estado: propuesta", "Estado: aceptada"))
        r.aplicar(ce.planear(r.dir, "T-001", hecha=True))
        self.assertIn("| [ADR-0003](0003-usar-flask.md) | Usar Flask | aceptada |", r.leer(ce.REL_INDICE))


# ---- propuestas de ADR e índice ----------------------------------------------------------------------
class DecisionesYAdr(unittest.TestCase):
    def test_numeracion_y_contenido_de_las_propuestas(self):
        r = Repo(self)
        avisos = []
        afectan = [{"titulo": "Usar Flask", "motivo": "es simple", "afecta": True},
                   {"titulo": "Guardar fechas en UTC", "motivo": "", "afecta": True}]
        p = ce.proponer_adrs(r.dir, "T-001", afectan, "docs/plan/reportes/T-001.md", avisos)
        self.assertEqual(sorted(p), ["docs/decisiones/0003-usar-flask.md", "docs/decisiones/0004-guardar-fechas-en-utc.md"])
        texto = p["docs/decisiones/0003-usar-flask.md"]
        self.assertEqual(texto.splitlines()[0], "# ADR-0003 · Usar Flask")
        self.assertIn("Estado: propuesta · Motivo: es simple · Afecta: T-001 y otras tareas (por precisar)", texto)
        self.assertIn("## Contexto", texto)
        self.assertIn("docs/plan/reportes/T-001.md", texto)
        self.assertIn("el reporte no la explica", p["docs/decisiones/0004-guardar-fechas-en-utc.md"])
        self.assertEqual(avisos, [])

    def test_sin_adr_previos_la_numeracion_empieza_en_1(self):
        r = Repo(self, con_mundo=False)
        p = ce.proponer_adrs(r.dir, "T-001", [{"titulo": "Algo", "motivo": "", "afecta": True}], "x", [])
        self.assertEqual(list(p), ["docs/decisiones/0001-algo.md"])

    def test_un_titulo_larguisimo_se_recorta(self):
        r = Repo(self)
        titulo = "una decisión " + "muy larga " * 30
        p = ce.proponer_adrs(r.dir, "T-001", [{"titulo": titulo, "motivo": "", "afecta": True}], "x", [])
        primera = next(iter(p.values())).splitlines()[0]
        self.assertLessEqual(len(primera), len("# ADR-0003 · ") + 91)
        self.assertTrue(primera.endswith("…"))

    def test_una_propuesta_repetida_no_se_duplica(self):
        r = Repo(self)
        r.poner("docs/decisiones/0003-usar-flask.md", adr("0003", "aceptada", "Usar Flask"))
        avisos = []
        p = ce.proponer_adrs(r.dir, "T-001", [{"titulo": "Usar Flask", "motivo": "", "afecta": True}], "x", avisos)
        self.assertEqual(p, {})
        self.assertTrue(hay(avisos, "ya existe una decisión llamada «Usar Flask»"))

    def test_la_propuesta_no_se_puede_usar_hasta_aceptarla(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.aplicar(r.cerrar(texto=reporte(decisiones="- Usar Flask · Motivo: es simple. Afecta a otras tareas")))
        r.poner("docs/plan/tareas/T-002.md", tarjeta_citando("docs/decisiones/0003-usar-flask.md"))
        res = bd.armar(r.dir, "T-002", forzar=True, home=r.dir / "sin-home")
        self.assertEqual(res.codigo, 1)
        self.assertTrue(hay(res.negativas, "ADR-0003 sigue en «propuesta»"))

    def test_el_indice_lista_todo_ordenado_y_el_bundle_no_lo_toma_por_un_adr(self):
        r = Repo(self)
        nuevo = {"docs/decisiones/0003-algo-con-barra.md": adr("0003", "propuesta", "Algo | con barra")}
        texto = ce.generar_indice(r.dir, nuevo)
        filas = [l for l in texto.splitlines() if l.startswith("| [ADR")]
        self.assertEqual(len(filas), 3)
        self.assertEqual(filas[0], "| [ADR-0001](0001-usar-una-base-de-datos-relacional.md) | Usar una base | aceptada |")
        self.assertEqual(filas[2], "| [ADR-0003](0003-algo-con-barra.md) | Algo / con barra | propuesta |")
        self.assertIsNone(bd.RE_ADR.match(ce.REL_INDICE))

    def test_sin_decisiones_no_se_crea_el_indice_pero_uno_existente_se_mantiene(self):
        r = Repo(self, con_mundo=False)
        self.assertIsNone(ce.generar_indice(r.dir, {}))
        r.poner(ce.REL_INDICE, "viejo\n")
        self.assertIn("(todavía no hay decisiones)", ce.generar_indice(r.dir, {}))

    def test_leer_adr(self):
        self.assertEqual(ce.leer_adr(adr("0007", "Aceptada", "Algo"), "0007"), ("0007", "Algo", "aceptada"))
        self.assertEqual(ce.leer_adr("nada\n", "0001"), ("0001", "(sin título)", "(sin estado)"))


def tarjeta_citando(adr_ruta):
    return (f"# T-002 · Registrar libro\nEstado: pendiente · Tamaño: S · Depende de: T-001 · Cubre: C1 (5)\nObjetivo: x\n"
            f"Leer (solo esto): docs/00-LEEME-IA.md · {adr_ruta}\nTocar: src/libros/*\n")


# ---- escritura y codificación ----------------------------------------------------------------------
class Escritura(unittest.TestCase):
    def test_si_algo_falla_todo_queda_como_estaba(self):
        r = Repo(self)
        r.poner(ce.REL_ESTADO, "VIEJO\n")
        r.poner("docs/bloqueado", "soy un archivo, no una carpeta")
        with self.assertRaises(OSError):
            ce._aplicar(r.dir, [("docs/nuevo.md", "x\n"), (ce.REL_ESTADO, "NUEVO\n"), ("docs/bloqueado/y.md", "y\n")], [])
        self.assertEqual(r.leer(ce.REL_ESTADO), "VIEJO\n", "lo que existía vuelve a su contenido")
        self.assertFalse((r.dir / "docs/nuevo.md").exists(), "lo que se creó se deshace")

    def test_si_falla_un_borrado_se_restaura_lo_ya_borrado_y_lo_escrito(self):
        r = Repo(self)
        r.poner(ce.REL_ESTADO, "VIEJO\n")
        original = Path.unlink

        def falla(self, *args, **kwargs):
            if self.name == "T-002.md":
                raise OSError("bloqueado")
            return original(self, *args, **kwargs)

        with mock.patch.object(Path, "unlink", falla):
            with self.assertRaises(OSError):
                ce._aplicar(r.dir, [(ce.REL_ESTADO, "NUEVO\n")], ["docs/plan/tareas/T-001.md", "docs/plan/tareas/T-002.md"])
        self.assertEqual(r.leer(ce.REL_ESTADO), "VIEJO\n")
        self.assertTrue((r.dir / "docs/plan/tareas/T-001.md").is_file(), "la tarjeta ya borrada vuelve")

    def test_se_escribe_en_utf8_sin_bom_y_con_saltos_lf(self):
        r = Repo(self)
        ce._aplicar(r.dir, [("docs/x.md", "línea con «comillas» y · separador\nsegunda\n")], [])
        crudo = (r.dir / "docs/x.md").read_bytes()
        self.assertFalse(crudo.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(crudo, "línea con «comillas» y · separador\nsegunda\n".encode("utf-8"))
        self.assertNotIn(b"\r", crudo)

    def test_toda_lectura_y_escritura_de_texto_declara_su_codificacion(self):
        # En Windows el predeterminado es cp1252 y falla con «·» y «»: nada debe depender de él.
        for nombre in ("init_diseno.py", "init_plan.py", "bundle.py", "cerrar.py", "validar.py",
                       "comprobar.py"):
            arbol = ast.parse((TOOLS / nombre).read_text(encoding="utf-8"))
            for nodo in ast.walk(arbol):
                if not isinstance(nodo, ast.Call):
                    continue
                f = nodo.func
                llamada = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
                claves = {k.arg for k in nodo.keywords}
                binario = (llamada == "open" and len(nodo.args) > 1 and isinstance(nodo.args[1], ast.Constant)
                           and "b" in str(nodo.args[1].value))
                if llamada in ("read_text", "write_text") or (llamada == "open" and not binario):
                    self.assertIn("encoding", claves, f"{nombre}:{nodo.lineno}: {llamada}() sin encoding")
                if llamada == "open" and not binario and len(nodo.args) > 1 and "w" in str(getattr(nodo.args[1], "value", "")):
                    self.assertIn("newline", claves, f"{nombre}:{nodo.lineno}: open(..., 'w') sin newline: en Windows "
                                                     "escribiría CRLF")
                if llamada == "run" and "text" in claves:
                    self.assertIn("encoding", claves, f"{nombre}:{nodo.lineno}: subprocess.run(text=True) sin encoding")


# ---- línea de comandos --------------------------------------------------------------------------------
class LineaDeComandos(unittest.TestCase):
    def reporte_en_raiz(self, r, tid="T-001", **kw):
        r.poner("reporte.md", reporte(tid, **kw))

    def test_de_punta_a_punta_con_el_ejemplo_del_metodo(self):
        r = RepoCli(self, con_mundo=False)
        r.poner("DISENO.md", DISENO)
        r.poner("PLAN.md", PLAN)
        r.poner("docs/00-LEEME-IA.md", "# Reglas\n")
        r.poner(".gitignore", "bundles/\n__pycache__/\ntools/\n")
        self.assertEqual(r.correr("init_diseno.py", "DISENO.md").returncode, 0)
        self.assertEqual(r.correr("init_plan.py", "PLAN.md").returncode, 0)
        for rel in ("docs/decisiones/0001-usar-una-base-de-datos-relacional.md", "docs/decisiones/0002-interfaz-web-sencilla-sin-app-movil.md"):
            r.poner(rel, r.leer(rel).replace("Estado: propuesta", "Estado: aceptada"))
        r.commit("diseño y plan")
        self.assertEqual(r.correr("bundle.py", "T-001").returncode, 0)
        r.trabajo_de_t001()                       # el trabajo del LLM, ya con su commit
        self.reporte_en_raiz(r, decisiones="- Usar Flask · Motivo: es simple. Afecta a otras tareas")
        p = r.cerrar_cli("T-001", "reporte.md", "--llm", "Claude")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("La tarea queda «en revisión»", p.stdout)
        self.assertIn("Commit ", p.stdout)
        self.assertIn("decisión que afecta a otras tareas: Usar Flask", p.stdout)
        self.assertIn("docs/decisiones/0003-usar-flask.md", p.stdout)
        self.assertNotIn("cambios sin guardar", p.stdout, "el propio reporte, sin commit, no cuenta como cambio sin guardar")
        self.assertFalse((r.dir / "reporte.md").exists(), "el reporte se movió desde la raíz")
        self.assertTrue((r.dir / "docs/plan/reportes/T-001.md").is_file())
        self.assertEqual(r.correr("bundle.py", "T-002").returncode, 1, "T-001 aún no está hecha")
        p = r.cerrar_cli("T-001", "--hecha")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("T-002: lista; arma su bundle con «python tools/bundle.py T-002»", p.stdout)
        self.assertEqual(r.correr("bundle.py", "T-002").returncode, 0)
        self.assertEqual(r.staged(), [], "cerrar.py y bundle.py nunca preparan nada en git")

    def test_check_no_escribe_ni_borra_nada(self):
        r = RepoCli(self)
        r.trabajo_de_t001()
        self.reporte_en_raiz(r)
        antes = r.archivos()
        p = r.cerrar_cli("T-001", "reporte.md", "--check")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("Modo --check: no se escribió ni se borró nada", p.stdout)
        self.assertIn("se borraría reporte.md", p.stdout)
        self.assertEqual(r.archivos(), antes)

    def test_check_de_hecha_no_borra_la_tarjeta(self):
        r = RepoCli(self)
        r.trabajo_de_t001()
        self.reporte_en_raiz(r)
        self.assertEqual(r.cerrar_cli("T-001", "reporte.md").returncode, 0)
        p = r.cerrar_cli("T-001", "--hecha", "--check")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("se borraría docs/plan/tareas/T-001.md", p.stdout)
        self.assertTrue((r.dir / "docs/plan/tareas/T-001.md").is_file())

    def test_un_reporte_fuera_del_repo_se_copia_y_el_original_no_se_toca(self):
        r = RepoCli(self)
        r.trabajo_de_t001()
        fuera = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, fuera, True)
        (fuera / "reporte.md").write_text(reporte(), encoding="utf-8")
        p = r.cerrar_cli("T-001", str(fuera / "reporte.md"))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((fuera / "reporte.md").exists())
        self.assertTrue((r.dir / "docs/plan/reportes/T-001.md").is_file())
        self.assertNotIn("borró", p.stdout)

    def test_un_reporte_con_bom_y_saltos_de_windows_se_guarda_en_lf(self):
        r = RepoCli(self)
        r.trabajo_de_t001()
        r.poner("reporte.md", como_bytes=b"\xef\xbb\xbf" + reporte().replace("\n", "\r\n").encode("utf-8"))
        p = r.cerrar_cli("T-001", "reporte.md")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        guardado = (r.dir / "docs/plan/reportes/T-001.md").read_bytes()
        self.assertEqual(guardado, reporte().encode("utf-8"))

    def test_los_errores_salen_con_1_y_no_escriben_nada(self):
        r = RepoCli(self)
        r.trabajo_de_t001()
        r.poner("reporte.md", sin_seccion(reporte(), "Supuestos"))
        antes = r.archivos()
        p = r.cerrar_cli("T-001", "reporte.md")
        self.assertEqual(p.returncode, 1)
        self.assertIn("falta la sección «## Supuestos»", p.stdout)
        self.assertIn("No se cerró T-001", p.stdout)
        self.assertEqual(r.archivos(), antes)

    def test_los_codigos_de_salida_de_uso(self):
        r = RepoCli(self)
        r.trabajo_de_t001()
        self.assertEqual(r.cerrar_cli("T-001").returncode, 2, "falta el reporte")
        self.assertEqual(r.cerrar_cli("T-001", "--hecha", "reporte.md").returncode, 2)
        self.assertEqual(r.cerrar_cli("T-001", "--hecha", "--parcial").returncode, 2)
        self.assertEqual(r.cerrar_cli("T-001", "no-existe.md").returncode, 2)
        self.reporte_en_raiz(r)
        self.assertEqual(r.cerrar_cli("T-009", "reporte.md").returncode, 2, "T-009 no tiene tarjeta")

    def test_un_reporte_que_no_esta_en_utf8_sale_con_1(self):
        r = RepoCli(self)
        r.trabajo_de_t001()
        r.poner("reporte.md", como_bytes=reporte().encode("cp1252", errors="replace").replace(b"?", "ñ".encode("latin-1")))
        p = r.cerrar_cli("T-001", "reporte.md")
        self.assertEqual(p.returncode, 1)
        self.assertIn("UTF-8", p.stdout)

    def test_el_reporte_ya_archivado_no_se_acepta(self):
        r = RepoCli(self)
        r.trabajo_de_t001()
        self.reporte_en_raiz(r)
        self.assertEqual(r.cerrar_cli("T-001", "reporte.md").returncode, 0)
        p = r.cerrar_cli("T-001", "docs/plan/reportes/T-001.md", "--reintento")
        self.assertEqual(p.returncode, 2)
        self.assertIn("ya está en docs/plan/reportes/", p.stdout)

    def test_el_parche_1_del_modo_estricto_recuerda_que_rojo_es_el_correcto(self):
        r = RepoCli(self)
        r.trabajo({"src/prestamos/__init__.py": "x\n", "tests/prestamos/test_p.py": "x\n"}, "test: parche 1")
        r.poner("reporte.md", reporte("T-003"))
        p = r.cerrar_cli("T-003", "reporte.md", "--parcial")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("La tarea queda «parcial»", p.stdout)
        self.assertIn("incorrecto: ImportError, ModuleNotFoundError, SyntaxError o NameError", p.stdout)
        self.assertIn("python tools/bundle.py T-003 --parche2", p.stdout)
        self.assertTrue((r.dir / "docs/plan/reportes/T-003-parche1.md").is_file())

    def test_el_reintento_se_pide_con_la_bandera(self):
        r = RepoCli(self)
        r.trabajo_de_t001()
        self.reporte_en_raiz(r)
        self.assertEqual(r.cerrar_cli("T-001", "reporte.md").returncode, 0)
        self.reporte_en_raiz(r)
        p = r.cerrar_cli("T-001", "reporte.md")
        self.assertEqual(p.returncode, 1)
        self.assertIn("usa --reintento", p.stdout)
        self.assertEqual(r.cerrar_cli("T-001", "reporte.md", "--reintento").returncode, 0)

    def test_una_consola_sin_acentos_no_tumba_el_programa(self):
        r = RepoCli(self)
        r.trabajo_de_t001()
        self.reporte_en_raiz(r)
        p = r.cerrar_cli("T-001", "reporte.md", env={"PYTHONIOENCODING": "ascii"})
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


# ---- trazabilidad del cierre: que commit y que LLM se anotan -------------------------------------
class Trazabilidad(unittest.TestCase):
    """Del piloto (H-28/H-29): ESTADO.md anoto el commit documental en vez del de la implementacion, y
    la columna LLM salio vacia. Las dos cosas se ven ahora al cerrar, que es cuando se pueden arreglar."""

    def corto(self, r, ref="HEAD"):
        return subprocess.run(["git", "rev-parse", "--short=7", ref], cwd=str(r.dir), capture_output=True,
                              text=True).stdout.strip()

    def test_por_defecto_anota_head(self):
        r = Repo(self)
        r.trabajo_de_t001()
        self.assertEqual(r.cerrar(llm="Claude").filas["T-001"]["commit"], self.corto(r))

    def test_commit_anota_el_que_le_digo_y_no_head(self):
        r = Repo(self)
        r.trabajo_de_t001()
        implementacion = self.corto(r)
        r.trabajo({"NOTAS.md": "apuntes"}, "docs: apuntes")      # el commit documental de despues
        c = r.cerrar(llm="Claude", commit="HEAD~1")
        self.assertEqual(c.filas["T-001"]["commit"], implementacion)
        self.assertNotEqual(c.filas["T-001"]["commit"], self.corto(r))

    def test_avisa_cuando_el_commit_anotado_no_toca_la_tarea(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.trabajo({"NOTAS.md": "apuntes"}, "docs: apuntes")
        c = r.cerrar(llm="Claude")                               # HEAD es el commit documental
        self.assertTrue(hay(c.avisos, "no cambió ningún archivo de «Tocar:»"), f"salió: {c.avisos}")

    def test_no_avisa_cuando_el_commit_anotado_si_toca_la_tarea(self):
        r = Repo(self)
        r.trabajo_de_t001()
        c = r.cerrar(llm="Claude")
        self.assertFalse(hay(c.avisos, "no cambió ningún archivo"), f"salió: {c.avisos}")

    def test_un_commit_que_no_existe_es_problema_de_entorno(self):
        r = Repo(self)
        r.trabajo_de_t001()
        c = r.cerrar(llm="Claude", commit="nada")
        self.assertEqual(c.codigo, 2)
        self.assertTrue(hay(c.negativas, "no encuentro el commit «nada»"), f"salió: {c.negativas}")

    def test_un_commit_que_parece_opcion_es_problema_de_entorno(self):
        r = Repo(self)
        r.trabajo_de_t001()
        c = r.cerrar(llm="Claude", commit="--output=algo")
        self.assertEqual(c.codigo, 2)
        self.assertTrue(hay(c.negativas, "--commit espera un commit"), f"salió: {c.negativas}")

    def test_sin_llm_avisa_de_la_celda_vacia(self):
        r = Repo(self)
        r.trabajo_de_t001()
        c = r.cerrar()
        self.assertTrue(hay(c.avisos, "nadie lo anotó"), f"salió: {c.avisos}")
        self.assertEqual(c.filas["T-001"]["llm"], "")

    def test_con_llm_no_avisa_y_lo_anota(self):
        r = Repo(self)
        r.trabajo_de_t001()
        c = r.cerrar(llm="Claude")
        self.assertFalse(hay(c.avisos, "nadie lo anotó"), f"salió: {c.avisos}")
        self.assertEqual(c.filas["T-001"]["llm"], "Claude")

    def test_en_un_reintento_no_vuelve_a_avisar_si_ya_estaba_anotado(self):
        r = Repo(self)
        r.trabajo_de_t001()
        r.aplicar(r.cerrar(llm="Claude"))
        c = r.cerrar(reintento=True)                             # sin --llm, pero la celda ya tiene valor
        self.assertFalse(hay(c.avisos, "nadie lo anotó"), f"salió: {c.avisos}")
        self.assertEqual(c.filas["T-001"]["llm"], "Claude")

    def test_hecha_no_acepta_commit(self):
        r = RepoCli(self)      # esta prueba va por la linea de comandos: el guardia esta en main()
        r.trabajo_de_t001()
        p = r.cerrar_cli("T-001", "--hecha", "--commit", "HEAD")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("--hecha se usa solo", p.stdout + p.stderr)



if __name__ == "__main__":
    unittest.main()
