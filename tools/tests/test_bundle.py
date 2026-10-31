"""Pruebas de tools/bundle.py. Solo usan la biblioteca estándar (y git, que el método ya exige).

Correr desde la raíz del repo:
    python -m unittest discover -s tools/tests -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
TOOLS = AQUI.parent
sys.path.insert(0, str(TOOLS))
import bundle as bd  # noqa: E402
import init_plan as ip  # noqa: E402

PLAN = (AQUI / "fixtures" / "PLAN-ejemplo.md").read_text(encoding="utf-8")
DISENO = (AQUI / "fixtures" / "DISENO-ejemplo.md").read_text(encoding="utf-8")
LEEME = "# Reglas para cualquier LLM\n\nContenido de prueba.\n"
REPARTO_PLAN = dict(ip.Plan(PLAN).analizar().reparto())  # backlog, cobertura y tarjetas reales del ejemplo


# ---- ayudas ---------------------------------------------------------------
def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=prueba", "-c", "user.email=prueba@example.com", *args],
                   cwd=str(cwd), check=True, capture_output=True)


def tarjeta(tid="T-002", titulo="Registrar libro", depende="T-001", leer="docs/00-LEEME-IA.md",
            tocar="src/libros/* · tests/libros/*", modo=None):
    lineas = [f"# {tid} · {titulo}", f"Estado: pendiente · Tamaño: S · Depende de: {depende} · Cubre: C1 (5), RF-001"]
    if modo:
        lineas.append(f"Modo: {modo}")
    lineas += ["Objetivo: algo", f"Leer (solo esto): {leer}", f"Tocar: {tocar}", "No tocar: src/prestamos/*",
               "Fuera de alcance: nada", "Criterios de aceptación (→ tests):", "  - uno",
               "Comando de test: ver docs/00-LEEME-IA.md", "Entrega: un parche (git diff) + reporte + comandos para aplicar"]
    return "\n".join(lineas) + "\n"


def adr(num="0001", estado="aceptada"):
    return f"# ADR-{num} · Una decisión\n\nEstado: {estado} · Motivo: x · Afecta: y\n"


def posicion(texto, fragmento):
    assert fragmento in texto, f"no encuentro {fragmento!r} en el bundle"
    return texto.index(fragmento)


def hay(lista, fragmento):
    return any(fragmento in x for x in lista)


class Repo:
    """Un repo de git temporal, con su carpeta personal aparte (para que no influya la tuya)."""

    def __init__(self, test, leeme=True, gitignore=True, con_git=True):
        self.dir = Path(tempfile.mkdtemp())
        self.home = Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, self.dir, True)
        test.addCleanup(shutil.rmtree, self.home, True)
        if con_git:
            git(self.dir, "init", "-q")
        if leeme:
            self.poner("docs/00-LEEME-IA.md", LEEME)
        if gitignore:
            self.poner(".gitignore", "bundles/\nsecreto.txt\n")

    def poner(self, rel, texto="", como_bytes=None):
        ruta = self.dir / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(como_bytes if como_bytes is not None else texto.encode("utf-8"))

    def quitar(self, rel):
        (self.dir / rel).unlink()

    def tarjeta(self, tid="T-002", **kw):
        self.poner(f"docs/plan/tareas/{tid}.md", tarjeta(tid, **kw))

    def backlog(self):
        self.poner(ip.REL_BACKLOG, REPARTO_PLAN[ip.REL_BACKLOG])

    def commit(self):
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-qm", "x", "--allow-empty")

    def armar(self, tarea="T-002", **kw):
        kw.setdefault("home", self.home)
        return bd.armar(self.dir, tarea, **kw)


class RepoCli(Repo):
    """Como Repo, pero con las herramientas copiadas, para probar la línea de comandos de verdad."""

    def __init__(self, test, **kw):
        super().__init__(test, **kw)
        for nombre in ("init_diseno.py", "init_plan.py", "bundle.py"):
            (self.dir / "tools").mkdir(exist_ok=True)
            shutil.copy(TOOLS / nombre, self.dir / "tools" / nombre)

    def correr(self, herramienta, *args, env=None):
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8", HOME=str(self.home), USERPROFILE=str(self.home))
        entorno.update(env or {})
        return subprocess.run([sys.executable, str(self.dir / "tools" / herramienta), *args], cwd=str(self.dir),
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno)

    def bundle(self, *args, env=None):
        return self.correr("bundle.py", *args, env=env)

    def leer(self, rel):
        return (self.dir / rel).read_text(encoding="utf-8")


# ---- la tarjeta -------------------------------------------------------------
class LecturaDeTarjetas(unittest.TestCase):
    def test_lee_una_tarjeta_real_del_plan_de_ejemplo(self):
        t = bd.Tarjeta(REPARTO_PLAN["docs/plan/tareas/T-003.md"])
        self.assertEqual((t.errores, t.avisos), ([], []))
        self.assertEqual((t.id, t.titulo, t.modo, t.depende), ("T-003", "Prestar y devolver libro", "estricto", ["T-002"]))
        self.assertEqual([i.ruta for i in t.leer], ["docs/00-LEEME-IA.md", "docs/requisitos/RF-002-prestar-libro.md", "docs/modelo.md"])
        self.assertEqual(t.leer[2].ancla, "prestamo")
        self.assertEqual([i.ruta for i in t.tocar], ["src/prestamos/*", "tests/prestamos/*"])

    def test_una_tarea_sin_dependencias(self):
        t = bd.Tarjeta(REPARTO_PLAN["docs/plan/tareas/T-001.md"])
        self.assertEqual((t.errores, t.depende, t.modo), ([], [], None))
        self.assertEqual(t.tocar[3].ruta, "docs/00-LEEME-IA.md")
        self.assertEqual(t.tocar[3].nota, "solo Convenciones y Comandos")

    def test_varias_dependencias(self):
        self.assertEqual(bd.Tarjeta(tarjeta(depende="T-001, T-003")).depende, ["T-001", "T-003"])

    def test_notas_anclas_y_quien_produce_un_archivo(self):
        t = bd.Tarjeta(tarjeta(leer="docs/modelo.md#actividad · src/api.py (lo produce T-003) · "
                                    "tests/libros/* (solo para ver qué debe seguir pasando)"))
        self.assertEqual(t.errores, [])
        self.assertEqual([(i.ruta, i.ancla, i.produce) for i in t.leer],
                         [("docs/modelo.md", "actividad", None), ("src/api.py", "", "T-003"), ("tests/libros/*", "", None)])

    def test_una_tarjeta_de_refactor_se_lee(self):
        t = bd.Tarjeta("# REF-01 · Ordenar préstamos\nEstado: pendiente · Tamaño: S · Depende de: — · Cubre: — (ordena)\n"
                       "Objetivo: x\nLeer (solo esto): docs/00-LEEME-IA.md · tests/prestamos/* (solo para ver)\n"
                       "Tocar: src/prestamos/*\nNo tocar: tests/* · docs/*\n")
        self.assertEqual((t.errores, t.id, t.depende), ([], "REF-01", []))

    def test_cada_error_de_la_tarjeta_se_dice(self):
        def sin(texto, prefijo):
            return "\n".join(l for l in texto.split("\n") if not l.startswith(prefijo))
        base = tarjeta()
        casos = [
            ("sin título", lambda t: sin(t, "# T-002"), "debe empezar con «# T-001 · Título»"),
            ("sin «Estado:»", lambda t: sin(t, "Estado:"), "falta la línea «Estado:"),
            ("«Estado:» sin «Depende de:»", lambda t: t.replace(" · Depende de: T-001", ""), "no trae «Depende de: …»"),
            ("«Depende de:» que no es una tarea", lambda t: t.replace("Depende de: T-001", "Depende de: la anterior"),
             "que no es una tarea"),
            ("sin «Leer:»", lambda t: sin(t, "Leer"), "falta la línea «Leer (solo esto):"),
            ("sin «Tocar:»", lambda t: sin(t, "Tocar:"), "falta la línea «Tocar:"),
            ("«Modo:» inválido", lambda t: t.replace("Objetivo:", "Modo: rapido\nObjetivo:"), "solo puede valer «estricto»"),
            ("un elemento que no es una ruta", lambda t: t.replace("Tocar: ", "Tocar: dos palabras sueltas · "),
             "no entiendo «dos palabras sueltas»"),
        ]
        for nombre, estropear, mensaje in casos:
            with self.subTest(nombre):
                t = bd.Tarjeta(estropear(base))
                self.assertTrue(hay([m for _, m in t.errores], mensaje), f"salió: {t.errores}")

    def test_los_campos_sin_llenar_son_un_aviso_no_un_error(self):
        t = bd.Tarjeta(tarjeta(leer="docs/00-LEEME-IA.md · «docs/modelo.md#entidad»", depende="«T-xxx, o —»"))
        self.assertEqual(t.errores, [])
        self.assertEqual(t.depende, [])
        self.assertTrue(hay([m for _, m in t.avisos], "sin llenar"))

    def test_los_comentarios_y_los_bloques_de_codigo_no_cuentan(self):
        texto = "<!--\nTocar: esto es de la plantilla\n-->\n" + tarjeta()
        self.assertEqual([i.ruta for i in bd.Tarjeta(texto).tocar], ["src/libros/*", "tests/libros/*"])


# ---- lo que arma y en qué orden ------------------------------------------------
class Armado(unittest.TestCase):
    def test_arma_con_las_secciones_en_el_orden_de_00_leeme_ia(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · docs/modelo.md", tocar="src/app.py")
        r.poner("docs/modelo.md", "# Modelo\n")
        r.poner("src/app.py", "print('hola')\n")
        res = r.armar("T-001")
        self.assertEqual((res.codigo, res.negativas, res.errores), (0, [], []))
        t = res.texto
        orden = [posicion(t, x) for x in ("## Árbol del repo", "## Entorno del usuario", "## Tarjeta T-001",
                                          "## Documentos que la tarjeta manda leer", "### docs/00-LEEME-IA.md",
                                          "### docs/modelo.md", "## Archivos de `Tocar:` que ya existen", "### src/app.py")]
        self.assertEqual(orden, sorted(orden))
        self.assertTrue(t.startswith("# Bundle de T-001 · Registrar libro\n"))
        self.assertIn("print('hola')", t)

    def test_las_reglas_viajan_primero_aunque_la_tarjeta_no_las_pida(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—", leer="docs/modelo.md", tocar="src/a.py")
        r.poner("docs/modelo.md", "# Modelo\n")
        t = r.armar("T-001").texto
        self.assertLess(posicion(t, "### docs/00-LEEME-IA.md"), posicion(t, "### docs/modelo.md"))

    def test_sin_las_reglas_no_hay_bundle(self):
        r = Repo(self, leeme=False)
        r.tarjeta("T-001", depende="—")
        res = r.armar("T-001")
        self.assertEqual(res.codigo, 1)
        self.assertTrue(hay(res.negativas, "no existe docs/00-LEEME-IA.md"))

    def test_el_arbol_lista_lo_que_existe_y_no_lo_ignorado_ni_lo_borrado(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—")
        r.poner("src/viejo.py", "x\n")
        r.commit()
        r.quitar("src/viejo.py")        # sigue en el índice de git, pero ya no existe
        r.poner("src/nuevo.py", "x\n")   # existe y git aún no lo conoce
        r.poner("secreto.txt", "clave")  # git lo ignora
        r.poner("bundles/T-009.md", "viejo")
        texto = r.armar("T-001").texto
        bloque = texto.split("## Árbol del repo")[1].split("## Entorno del usuario")[0]
        self.assertIn("src/nuevo.py", bloque)
        self.assertIn("docs/plan/tareas/T-001.md", bloque)
        for no_debe in ("src/viejo.py", "secreto.txt", "bundles/T-009.md"):
            self.assertNotIn(no_debe, bloque)
        lineas = [l for l in bloque.splitlines() if "/" in l or l.startswith(".")]
        self.assertEqual(lineas, sorted(lineas), "el árbol va ordenado")

    def test_los_archivos_de_tocar_que_existen_van_una_sola_vez_y_los_nuevos_se_avisan(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · docs/modelo.md",
                  tocar="src/libros/* · docs/modelo.md (solo la sección Actividad) · tests/libros/* · src/nuevo.py")
        r.poner("src/libros/a.py", "A\n")
        r.poner("src/libros/sub/b.py", "B\n")   # el * es recursivo
        r.poner("docs/modelo.md", "# Modelo\n")
        res = r.armar("T-001")
        t = res.texto
        self.assertEqual(t.count("### docs/modelo.md"), 1, "un archivo de Leer y de Tocar viaja una sola vez")
        self.assertIn("### src/libros/a.py", t)
        self.assertIn("### src/libros/sub/b.py", t)
        self.assertIn("Por crear (no existen todavía): tests/libros/*; src/nuevo.py", t)
        self.assertEqual([x for s, x, _ in res.incluidos if s == "tocar"], ["src/libros/a.py", "src/libros/sub/b.py"])

    def test_sin_archivos_de_tocar_existentes_lo_dice(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—", tocar="src/*")
        self.assertIn("Ninguno todavía: la tarea los crea.", r.armar("T-001").texto)

    def test_un_ancla_se_senala_y_va_el_archivo_completo(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · docs/modelo.md#libro")
        r.poner("docs/modelo.md", "# Modelo\n- LIBRO: *id\n")
        t = r.armar("T-001").texto
        self.assertIn("La tarjeta pide la parte «#libro»; va el archivo completo.", t)
        self.assertIn("- LIBRO: *id", t)

    def test_la_valla_crece_si_el_archivo_ya_trae_vallas(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · docs/a.md · docs/b.md")
        r.poner("docs/a.md", "antes\n```python\nx = 1\n```\ndespués\n")
        r.poner("docs/b.md", "````\ncuatro\n````\n")
        t = r.armar("T-001").texto
        self.assertIn("````\nantes\n```python\nx = 1\n```\ndespués\n````\n", t)
        self.assertIn("`````\n````\ncuatro\n````\n`````\n", t)

    def test_cada_valla_cierra_aunque_el_archivo_no_termine_en_salto_de_linea(self):
        self.assertEqual(bd._bloque("sin salto"), "````\nsin salto\n````\n")
        self.assertEqual(bd._bloque(""), "````\n````\n")

    def test_los_saltos_de_windows_y_el_bom_no_llegan_al_bundle(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · docs/a.md")
        r.poner("docs/a.md", como_bytes=b"\xef\xbb\xbflinea 1\r\nlinea 2\r\n")
        t = r.armar("T-001").texto
        self.assertNotIn("\r", t)
        self.assertNotIn("\ufeff", t)
        self.assertIn("````\nlinea 1\nlinea 2\n````", t)

    def test_un_archivo_binario_o_que_no_es_utf8_se_omite_con_aviso(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · docs/img.bin · docs/latin.txt")
        r.poner("docs/img.bin", como_bytes=b"\x89PNG\r\n\x1a\n\x00\x00")
        r.poner("docs/latin.txt", como_bytes="canción".encode("latin-1"))
        res = r.armar("T-001")
        self.assertEqual(res.codigo, 0)
        self.assertTrue(hay(res.avisos, "docs/img.bin se omitió: es un archivo binario"))
        self.assertTrue(hay(res.avisos, "docs/latin.txt se omitió: no está en UTF-8"))
        self.assertNotIn("### docs/img.bin", res.texto)

    def test_una_tarjeta_nunca_lee_fuera_del_repo(self):
        r = Repo(self)
        fuera = r.dir.parent / "fuera-del-repo.txt"
        fuera.write_text("SECRETO", encoding="utf-8")
        self.addCleanup(fuera.unlink)
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · ../fuera-del-repo.txt", tocar="../fuera-del-repo.txt")
        res = r.armar("T-001")
        self.assertEqual(res.codigo, 1)
        self.assertTrue(hay(res.negativas, "../fuera-del-repo.txt (de «Leer:») no existe"))
        self.assertNotIn("SECRETO", res.texto or "")

    def test_las_mayusculas_no_importan_al_pedir_la_tarea(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—")
        self.assertEqual(r.armar("t-001").codigo, 0)

    def test_una_tarea_de_refactor_se_arma(self):
        r = Repo(self)
        r.poner("docs/plan/tareas/REF-01.md",
                "# REF-01 · Ordenar\nEstado: pendiente · Tamaño: S · Depende de: — · Cubre: — (ordena)\n"
                "Objetivo: x\nLeer (solo esto): docs/00-LEEME-IA.md · tests/prestamos/* (solo para ver)\n"
                "Tocar: src/prestamos/*\n")
        r.poner("tests/prestamos/test_a.py", "def test_a(): pass\n")
        r.poner("src/prestamos/a.py", "A\n")
        res = r.armar("REF-01")
        self.assertEqual((res.codigo, res.negativas), (0, []))
        self.assertIn("### tests/prestamos/test_a.py", res.texto)
        self.assertIn("### src/prestamos/a.py", res.texto)


# ---- las compuertas ------------------------------------------------------------------
class Compuertas(unittest.TestCase):
    def repo_con_adr(self, estado, **kw):
        r = Repo(self)
        r.poner("docs/decisiones/0001-una-decision.md", adr("0001", estado))
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · docs/decisiones/0001-una-decision.md", **kw)
        return r

    def test_un_adr_aceptado_deja_pasar(self):
        res = self.repo_con_adr("aceptada").armar("T-001")
        self.assertEqual((res.codigo, res.negativas), (0, []))
        self.assertIn("### docs/decisiones/0001-una-decision.md", res.texto)

    def test_un_adr_que_no_esta_aceptado_se_niega_y_dice_por_que(self):
        casos = [("propuesta", "ADR-0001 sigue en «propuesta». Solo tú la pasas a «aceptada»"),
                 ("reemplazada", "ADR-0001 está «reemplazada»"),
                 ("borrador", "el estado «borrador» no es válido")]
        for estado, mensaje in casos:
            with self.subTest(estado):
                res = self.repo_con_adr(estado).armar("T-001")
                self.assertEqual((res.codigo, res.texto), (1, None))
                self.assertTrue(hay(res.negativas, mensaje), res.negativas)

    def test_un_adr_sin_linea_de_estado_se_niega(self):
        r = Repo(self)
        r.poner("docs/decisiones/0001-una-decision.md", "# ADR-0001 · Algo\n\nSin estado.\n")
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · docs/decisiones/0001-una-decision.md")
        self.assertTrue(hay(r.armar("T-001").negativas, "no encuentro su línea «Estado: …»"))

    def test_forzar_no_salta_la_compuerta_de_los_adr(self):
        res = self.repo_con_adr("propuesta").armar("T-001", forzar=True)
        self.assertEqual(res.codigo, 1)

    def test_se_avisan_todos_los_adr_pendientes_de_una_vez(self):
        r = Repo(self)
        r.poner("docs/decisiones/0001-a.md", adr("0001", "propuesta"))
        r.poner("docs/decisiones/0002-b.md", adr("0002", "propuesta"))
        r.poner("docs/decisiones/README.md", "# Índice de decisiones\n")  # no es un ADR: no se revisa
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · docs/decisiones/*")
        res = r.armar("T-001")
        self.assertEqual(len(res.negativas), 2, res.negativas)

    def test_una_dependencia_cuya_tarjeta_sigue_existiendo_no_esta_hecha(self):
        r = Repo(self)
        r.backlog()
        r.tarjeta("T-001", depende="—")
        r.tarjeta("T-002", depende="T-001")
        res = r.armar("T-002")
        self.assertEqual((res.codigo, res.texto), (1, None))
        self.assertTrue(hay(res.negativas, "T-001 no está hecha: su tarjeta docs/plan/tareas/T-001.md todavía existe"))

    def test_una_dependencia_sin_tarjeta_esta_hecha(self):
        r = Repo(self)
        r.backlog()
        r.tarjeta("T-002", depende="T-001")
        res = r.armar("T-002")
        self.assertEqual((res.codigo, res.negativas), (0, []))
        self.assertEqual(res.notas, ["T-001 está hecha (su tarjeta ya no existe)"])

    def test_forzar_salta_las_dependencias_y_lo_deja_escrito_en_el_bundle(self):
        r = Repo(self)
        r.backlog()
        r.tarjeta("T-001", depende="—")
        r.tarjeta("T-002", depende="T-001")
        res = r.armar("T-002", forzar=True)
        self.assertEqual(res.codigo, 0)
        self.assertTrue(hay(res.avisos, "saltaste la compuerta de dependencias (--forzar)"))
        self.assertIn("**Dependencias no hechas** (se saltó la compuerta con --forzar): T-001.", res.texto)

    def test_una_dependencia_que_no_existe_en_el_backlog_se_niega_ni_con_forzar(self):
        r = Repo(self)
        r.backlog()
        r.tarjeta("T-002", depende="T-999")
        for forzar in (False, True):
            res = r.armar("T-002", forzar=forzar)
            self.assertEqual(res.codigo, 1)
            self.assertTrue(hay(res.negativas, "T-999, de «Depende de:», no está en docs/plan/backlog.md"))

    def test_sin_backlog_se_avisa_y_se_usa_solo_la_tarjeta(self):
        r = Repo(self)
        r.tarjeta("T-002", depende="T-001")
        res = r.armar("T-002")
        self.assertEqual(res.codigo, 0)
        self.assertTrue(hay(res.avisos, "no encontré docs/plan/backlog.md"))

    def test_un_backlog_ilegible_se_avisa(self):
        r = Repo(self)
        r.poner(ip.REL_BACKLOG, "esto no es un backlog\n")
        r.tarjeta("T-002", depende="T-001")
        res = r.armar("T-002")
        self.assertEqual(res.codigo, 0)
        self.assertTrue(hay(res.avisos, "no pude leer docs/plan/backlog.md"))

    def test_un_archivo_de_leer_que_no_existe_y_nadie_produce_se_niega(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · docs/falta.md")
        res = r.armar("T-001")
        self.assertEqual(res.codigo, 1)
        self.assertTrue(hay(res.negativas, "docs/falta.md (de «Leer:») no existe y la tarjeta no dice qué tarea lo produce"))

    def test_un_patron_de_leer_sin_coincidencias_se_niega(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—", leer="docs/00-LEEME-IA.md · tests/prestamos/*")
        self.assertTrue(hay(r.armar("T-001").negativas, "tests/prestamos/* (de «Leer:») no existe"))

    def test_un_archivo_que_produce_una_tarea_pendiente_se_acepta_como_por_crear(self):
        r = Repo(self)
        r.backlog()
        r.tarjeta("T-003", depende="—", leer="docs/00-LEEME-IA.md · src/api.py (lo produce T-002)")
        r.tarjeta("T-002", depende="—")  # T-002 todavía no está hecha
        res = r.armar("T-003")
        self.assertEqual((res.codigo, res.negativas), (0, []))
        self.assertIn("Todavía no existen (los producen tareas previas): src/api.py (lo produce T-002)", res.texto)

    def test_un_archivo_que_debia_producir_una_tarea_ya_hecha_se_niega(self):
        r = Repo(self)
        r.backlog()
        r.tarjeta("T-003", depende="—", leer="docs/00-LEEME-IA.md · src/api.py (lo produce T-002)")  # sin tarjeta de T-002
        res = r.armar("T-003")
        self.assertEqual(res.codigo, 1)
        self.assertTrue(hay(res.negativas, "la tarjeta dice que lo produce T-002, que ya está hecha, pero el archivo no existe"))

    def test_se_dicen_todos_los_motivos_juntos(self):
        r = Repo(self)
        r.backlog()
        r.poner("docs/decisiones/0001-a.md", adr("0001", "propuesta"))
        r.tarjeta("T-001", depende="—")
        r.tarjeta("T-002", depende="T-001", leer="docs/00-LEEME-IA.md · docs/decisiones/0001-a.md · docs/falta.md")
        res = r.armar("T-002")
        self.assertEqual(len(res.negativas), 3, res.negativas)


# ---- modo estricto -----------------------------------------------------------------------
class ModoEstricto(unittest.TestCase):
    def repo_estricto(self, con_tests=True):
        r = Repo(self)
        r.tarjeta("T-003", depende="—", modo="estricto", tocar="src/prestamos/* · tests/prestamos/*")
        r.poner("src/prestamos/__init__.py", "def prestar():\n    raise NotImplementedError\n")
        if con_tests:
            r.poner("tests/prestamos/test_prestamos.py", "def test_prestar():\n    assert False\n")
        return r

    def test_parche2_suma_los_tests_del_parche_1_una_sola_vez(self):
        res = self.repo_estricto().armar("T-003", parche2=True)
        t = res.texto
        self.assertEqual((res.codigo, res.negativas), (0, []))
        self.assertIn("**Modo estricto, parche 2.**", t)
        self.assertIn("### Tests del parche 1 (también en `No tocar:`)", t)
        self.assertEqual(t.count("### tests/prestamos/test_prestamos.py"), 1)
        self.assertLess(posicion(t, "### tests/prestamos/test_prestamos.py"), posicion(t, "## Archivos de `Tocar:`"))
        self.assertGreater(posicion(t, "### src/prestamos/__init__.py"), posicion(t, "## Archivos de `Tocar:`"))
        self.assertEqual([x for s, x, _ in res.incluidos if s == "tests"], ["tests/prestamos/test_prestamos.py"])
        self.assertEqual([x for s, x, _ in res.incluidos if s == "tocar"], ["src/prestamos/__init__.py"])

    def test_sin_tests_del_parche_1_parche2_se_niega(self):
        res = self.repo_estricto(con_tests=False).armar("T-003", parche2=True)
        self.assertEqual(res.codigo, 1)
        self.assertTrue(hay(res.negativas, "esperaba los tests del parche 1"))

    def test_parche2_solo_sirve_en_modo_estricto(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—")
        res = r.armar("T-001", parche2=True)
        self.assertEqual(res.codigo, 1)
        self.assertTrue(hay(res.negativas, "--parche2 solo sirve con una tarjeta de «Modo: estricto»"))

    def test_el_parche_1_es_el_bundle_normal_y_avisa_si_parece_el_2(self):
        res = self.repo_estricto(con_tests=False).armar("T-003")
        self.assertEqual(res.codigo, 0)
        self.assertNotIn("parche 2", res.texto)
        self.assertFalse(hay(res.avisos, "Si es el parche 2"))
        res = self.repo_estricto(con_tests=True).armar("T-003")  # ya hay tests y no se pidió --parche2
        self.assertEqual(res.codigo, 0)
        self.assertTrue(hay(res.avisos, "Si es el parche 2, vuelve a armar el bundle con --parche2"))

    def test_si_la_tarjeta_ya_lista_los_tests_en_leer_van_una_sola_vez(self):
        r = Repo(self)
        r.tarjeta("T-003", depende="—", modo="estricto", leer="docs/00-LEEME-IA.md · tests/prestamos/*",
                  tocar="src/prestamos/* · tests/prestamos/*")
        r.poner("tests/prestamos/test_prestamos.py", "def test_x(): pass\n")
        t = r.armar("T-003", parche2=True).texto
        self.assertEqual(t.count("### tests/prestamos/test_prestamos.py"), 1)
        self.assertIn("Los tests del parche 1 ya van arriba, entre los documentos de `Leer:`.", t)


# ---- entorno del usuario, tamaño y avisos --------------------------------------------------------
class EntornoYAvisos(unittest.TestCase):
    def repo(self):
        r = Repo(self)
        r.tarjeta("T-001", depende="—")
        return r

    def test_el_entorno_sale_de_metodo_ia_json(self):
        r = self.repo()
        (r.home / ".metodo-ia.json").write_text(json.dumps({"terminal": "PowerShell", "carpeta_parches": "C:\\Users\\x\\Downloads"}),
                                                encoding="utf-8")
        res = r.armar("T-001")
        self.assertIn("- Terminal: PowerShell\n- Carpeta de parches: C:\\Users\\x\\Downloads\n- Carpeta del repo: " + str(r.dir), res.texto)
        self.assertFalse(hay(res.avisos, "metodo-ia"))

    def test_powershell_guarda_con_bom_y_tambien_se_lee(self):
        r = self.repo()
        (r.home / ".metodo-ia.json").write_bytes(b"\xef\xbb\xbf" + json.dumps({"terminal": "PowerShell", "carpeta_parches": "D"}).encode())
        self.assertIn("- Terminal: PowerShell", r.armar("T-001").texto)

    def test_si_falta_se_dice_sin_inventar_y_se_avisa(self):
        res = self.repo().armar("T-001")
        self.assertIn("- Terminal: (sin configurar)\n- Carpeta de parches: (sin configurar)", res.texto)
        self.assertTrue(hay(res.avisos, "«terminal» ni «carpeta_parches»"))

    def test_un_entorno_incompleto_solo_marca_lo_que_falta(self):
        r = self.repo()
        (r.home / ".metodo-ia.json").write_text(json.dumps({"terminal": "CMD"}), encoding="utf-8")
        res = r.armar("T-001")
        self.assertIn("- Terminal: CMD\n- Carpeta de parches: (sin configurar)", res.texto)
        self.assertTrue(hay(res.avisos, "no trae «carpeta_parches»"))
        self.assertFalse(hay(res.avisos, "«terminal»"))

    def test_un_json_roto_o_con_valores_raros_no_tumba_nada(self):
        for contenido in ("{no es json", "[1, 2]", json.dumps({"terminal": 5, "carpeta_parches": ["x"]})):
            with self.subTest(contenido):
                r = self.repo()
                (r.home / ".metodo-ia.json").write_text(contenido, encoding="utf-8")
                res = r.armar("T-001")
                self.assertEqual(res.codigo, 0)
                self.assertIn("(sin configurar)", res.texto)
                self.assertTrue(hay(res.avisos, "metodo-ia"))

    def test_avisa_si_el_bundle_es_demasiado_grande(self):
        r = self.repo()
        r.poner("src/libros/grande.py", "x = 1\n" * 400)
        r.tarjeta("T-001", depende="—", tocar="src/libros/*")
        self.assertFalse(hay(r.armar("T-001").avisos, "pesa"))
        res = r.armar("T-001", max_kb=1)
        self.assertTrue(hay(res.avisos, "el límite es 1 KB"))
        self.assertEqual(res.codigo, 0, "es un aviso, no impide armarlo")

    def test_avisa_de_cambios_sin_guardar(self):
        r = self.repo()
        r.commit()
        self.assertFalse(hay(r.armar("T-001").avisos, "cambios sin guardar"))
        r.poner("src/nuevo.py", "x\n")
        self.assertTrue(hay(r.armar("T-001").avisos, "1 archivo(s) con cambios sin guardar"))

    def test_avisa_si_bundles_no_esta_ignorado(self):
        r = Repo(self, gitignore=False)
        r.tarjeta("T-001", depende="—")
        self.assertTrue(hay(r.armar("T-001").avisos, "bundles/ no está en .gitignore"))
        self.assertFalse(hay(self.repo().armar("T-001").avisos, ".gitignore"))

    def test_una_tarjeta_con_errores_no_arma_nada(self):
        r = Repo(self)
        r.poner("docs/plan/tareas/T-001.md", "# T-001 · Rota\nEstado: pendiente · Depende de: —\n")
        res = r.armar("T-001")
        self.assertEqual((res.codigo, res.texto), (1, None))
        self.assertTrue(hay([m for _, m in res.errores], "falta la línea «Tocar:"))

    def test_el_titulo_debe_coincidir_con_el_archivo(self):
        r = Repo(self)
        r.poner("docs/plan/tareas/T-002.md", tarjeta("T-009"))
        res = r.armar("T-002")
        self.assertEqual(res.codigo, 1)
        self.assertTrue(hay([m for _, m in res.errores], "el título dice T-009, pero el archivo es T-002.md"))

    def test_sin_tarjeta_o_con_un_numero_raro_sale_con_2(self):
        r = Repo(self)
        res = r.armar("T-007")
        self.assertEqual(res.codigo, 2)
        self.assertTrue(hay(res.negativas, "no existe la tarjeta docs/plan/tareas/T-007.md"))
        self.assertEqual(r.armar("hola").codigo, 2)

    def test_fuera_de_un_repo_de_git_sale_con_2(self):
        r = Repo(self, con_git=False)
        r.tarjeta("T-001", depende="—")
        res = r.armar("T-001")
        self.assertEqual(res.codigo, 2)
        self.assertTrue(hay(res.negativas, "git no pudo listar los archivos"))

    def test_las_estimaciones_de_tamano(self):
        self.assertEqual(bd._kb(1536), "1.5 KB")
        self.assertEqual(bd._tokens("x" * 400), "100")
        self.assertEqual(bd._tokens("x" * 12345), "3.100")  # 3.086 redondeado a la centena


# ---- línea de comandos -------------------------------------------------------------------------------
class LineaDeComandos(unittest.TestCase):
    def test_de_punta_a_punta_con_el_ejemplo_del_metodo(self):
        r = RepoCli(self)
        r.poner("DISENO.md", DISENO)
        r.poner("PLAN.md", PLAN)
        self.assertEqual(r.correr("init_diseno.py", "DISENO.md").returncode, 0)
        self.assertEqual(r.correr("init_plan.py", "PLAN.md").returncode, 0)
        r.commit()
        # 1. los ADR del ejemplo están en «propuesta»: T-001 se niega
        p = r.bundle("T-001")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("ADR-0001 sigue en «propuesta»", p.stdout)
        self.assertIn("ADR-0002 sigue en «propuesta»", p.stdout)
        self.assertFalse((r.dir / "bundles").exists())
        # 2. los acepto y se arma
        for rel in ("docs/decisiones/0001-usar-una-base-de-datos-relacional.md", "docs/decisiones/0002-interfaz-web-sencilla-sin-app-movil.md"):
            r.poner(rel, r.leer(rel).replace("Estado: propuesta", "Estado: aceptada"))
        r.commit()
        p = r.bundle("T-001")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((r.dir / "bundles" / "T-001.md").is_file())
        self.assertIn("Incluye: el árbol", p.stdout)
        self.assertIn("tokens", p.stdout)
        # 3. T-002 depende de T-001, cuya tarjeta todavía existe
        p = r.bundle("T-002")
        self.assertEqual(p.returncode, 1)
        self.assertIn("T-001 no está hecha", p.stdout)
        self.assertEqual(r.bundle("T-002", "--forzar").returncode, 0)
        # 4. se cierra T-001 (se borra su tarjeta) y T-002 se arma sin forzar
        (r.dir / "docs/plan/tareas/T-001.md").unlink()
        p = r.bundle("T-002")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("Dependencias: T-001 está hecha", p.stdout)
        self.assertIn("### docs/requisitos/RF-001-registrar-libro.md", r.leer("bundles/T-002.md"))
        # 5. los bundles no ensucian git
        status = subprocess.run(["git", "status", "--short"], cwd=str(r.dir), capture_output=True, text=True).stdout
        self.assertNotIn("bundles", status)

    def test_lee_el_entorno_de_la_carpeta_personal(self):
        r = RepoCli(self)
        r.tarjeta("T-001", depende="—")
        (r.home / ".metodo-ia.json").write_text(json.dumps({"terminal": "PowerShell", "carpeta_parches": "X"}), encoding="utf-8")
        p = r.bundle("T-001")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("- Terminal: PowerShell", r.leer("bundles/T-001.md"))
        self.assertNotIn("metodo-ia", p.stdout)

    def test_el_bundle_se_escribe_con_saltos_lf(self):
        r = RepoCli(self)
        r.tarjeta("T-001", depende="—")
        r.poner("docs/00-LEEME-IA.md", como_bytes=b"reglas\r\ncon windows\r\n")
        self.assertEqual(r.bundle("T-001").returncode, 0)
        self.assertNotIn(b"\r", (r.dir / "bundles" / "T-001.md").read_bytes())

    def test_los_codigos_de_salida(self):
        r = RepoCli(self)
        self.assertEqual(r.bundle("T-001").returncode, 2)       # no hay tarjeta
        self.assertEqual(r.bundle("hola").returncode, 2)        # no es una tarea
        r.tarjeta("T-001", depende="—")
        self.assertEqual(r.bundle("T-001", "--max-kb", "0").returncode, 2)  # argumento inválido
        self.assertEqual(r.bundle("T-001").returncode, 0)

    def test_una_consola_sin_acentos_no_tumba_el_programa(self):
        r = RepoCli(self)
        r.tarjeta("T-001", depende="—")
        p = r.bundle("T-001", env={"PYTHONIOENCODING": "ascii"})
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
