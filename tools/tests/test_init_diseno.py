"""Pruebas de tools/init_diseno.py. Solo usan la biblioteca estándar.

Correr desde la raíz del repo:
    python -m unittest discover -s tools/tests -v
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
TOOLS = AQUI.parent
sys.path.insert(0, str(TOOLS))
import init_diseno as idz  # noqa: E402

EJEMPLO = (AQUI / "fixtures" / "DISENO-ejemplo.md").read_text(encoding="utf-8")
PLANTILLA = TOOLS.parent / "docs" / "plantillas" / "diseno.md"
TODAS_LAS_SECCIONES = ["Problema y objetivo", "Actores", "Alcance (dentro / fuera)", "Criterios de éxito",
                       "Reglas y restricciones", "Tecnología (decidida / pendiente)", "Preguntas abiertas",
                       "Supuestos"]


# ---- ayudas ---------------------------------------------------------------
def analizar(texto):
    return idz.Diseno(texto).analizar()


def con(texto, viejo, nuevo):
    assert viejo in texto, f"la prueba está mal escrita: no encuentro {viejo!r}"
    return texto.replace(viejo, nuevo, 1)


def sin_linea(texto, fragmento):
    lineas = texto.split("\n")
    i = next(k for k, l in enumerate(lineas) if fragmento in l)
    return "\n".join(lineas[:i] + lineas[i + 1:])


def linea_de(texto, fragmento, ultima=False):
    numeros = [k + 1 for k, l in enumerate(texto.split("\n")) if fragmento in l]
    return numeros[-1] if ultima else numeros[0]


def tiene_error(d, mensaje, linea=None):
    return any(mensaje in m and (linea is None or n == linea) for n, m in d.errores)


class RepoTemporal:
    """Un repo de mentira con solo tools/init_diseno.py, para probar la línea de comandos."""

    def __init__(self, test):
        self.dir = Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, self.dir, True)
        (self.dir / "tools").mkdir()
        shutil.copy(TOOLS / "init_diseno.py", self.dir / "tools" / "init_diseno.py")

    def correr(self, *args, env=None):
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
        entorno.update(env or {})
        return subprocess.run([sys.executable, str(self.dir / "tools" / "init_diseno.py"), *args],
                              cwd=self.dir, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=entorno)

    def archivos(self):
        return sorted(p.relative_to(self.dir).as_posix() for p in self.dir.rglob("*")
                      if p.is_file() and "__pycache__" not in p.parts)


# ---- formato --------------------------------------------------------------
class Formato(unittest.TestCase):
    def test_el_ejemplo_es_valido(self):
        d = analizar(EJEMPLO)
        self.assertEqual(d.errores, [])
        self.assertEqual([r["id"] for r in d.rfs], ["RF-001", "RF-002", "RF-003"])
        self.assertEqual([a["id"] for a in d.adrs], ["ADR-0001", "ADR-0002"])
        self.assertEqual(sorted(d.criterios), ["C1", "C2", "C3"])
        self.assertEqual(sorted(d.preguntas), ["P-01", "P-02", "P-03"])
        self.assertEqual(d.nombre, "Biblioteca de barrio")

    @unittest.skipUnless(PLANTILLA.is_file(), "no está docs/plantillas/diseno.md")
    def test_la_plantilla_de_diseno_cumple_el_formato(self):
        d = analizar(PLANTILLA.read_text(encoding="utf-8"))
        self.assertEqual(d.errores, [], "la plantilla y el analizador deben estar de acuerdo")
        self.assertTrue(any("sin llenar" in m for _, m in d.avisos))

    def test_cada_error_se_detecta_con_su_linea(self):
        todas = lambda t: "\n".join(l for l in t.split("\n") if not l.startswith("|"))  # noqa: E731
        casos = [
            # (nombre, cómo se estropea el ejemplo, mensaje esperado, fragmento que marca la línea; 0 = sin línea)
            ("falta una sección", lambda t: sin_linea(t, "## Actores"), "falta la sección «## Actores»", 0),
            ("título mal escrito", lambda t: con(t, "## Alcance (dentro / fuera)", "## Alcance (dentro/fuera)"),
             "¿quisiste decir «Alcance (dentro / fuera)»?", "## Alcance (dentro/fuera)"),
            ("sección repetida", lambda t: t + "\n## Actores\n- otro\n", "está repetida", ("## Actores", True)),
            ("RF sin «Aporta a»", lambda t: sin_linea(t, "Aporta a: C2"), "RF-003", "### RF-003"),
            ("RF con línea en blanco antes de «Aporta a»",
             lambda t: con(t, "### RF-001 · Registrar libro\n", "### RF-001 · Registrar libro\n\n"),
             "debe ir en la línea siguiente al título", "### RF-001"),
            ("«Aporta a» cita un criterio inexistente", lambda t: con(t, "Aporta a: C1, C3", "Aporta a: C1, C9"),
             "cita C9", "### RF-001"),
            ("RF sin «Criterios de aceptación:»", lambda t: sin_linea(t, "Criterios de aceptación:"),
             "falta la línea «Criterios de aceptación:»", "### RF-001"),
            ("RF sin criterios",
             lambda t: sin_linea(sin_linea(t, "- Se listan los préstamos"), "- La lista muestra"),
             "no hay criterios de aceptación", None),
            ("RF repetido", lambda t: con(t, "### RF-003 · Listar atrasos", "### RF-002 · Listar atrasos"),
             "RF-002 está repetido", "### RF-002 · Listar atrasos"),
            ("subtítulo desconocido en Funcionalidades",
             lambda t: con(t, "### RF-003 · Listar atrasos", "### Notas\n\n### RF-003 · Listar atrasos"),
             "los requisitos se escriben", "### Notas"),
            ("RF escrito como sección",
             lambda t: con(t, "### RF-003 · Listar atrasos", "## RF-003 · Listar atrasos"),
             "van con «###»", "## RF-003"),
            ("ADR con estado inválido",
             lambda t: con(t, "Estado: propuesta · Motivo: los datos", "Estado: pendiente · Motivo: los datos"),
             "estado «pendiente» no es válido", "Estado: pendiente"),
            ("ADR con la plantilla sin llenar",
             lambda t: con(t, "Estado: propuesta · Motivo: los datos",
                           "Estado: propuesta | aceptada | reemplazada · Motivo: los datos"),
             "la línea siguiente al título debe ser", "### ADR-0001"),
            ("cabecera de la tabla distinta", lambda t: con(t, "| ID | Criterio | Peso |", "| ID | Criterio | Puntaje |"),
             "la cabecera de la tabla debe ser", "| ID | Criterio | Puntaje |"),
            ("peso que no es número", lambda t: con(t, "| 5 | propio |", "| cinco | propio |"),
             "debe ser un número mayor que 0", "| cinco |"),
            ("criterio repetido", lambda t: con(t, "| C2 |", "| C1 |"), "el criterio C1 está repetido",
             "| C1 | La bibliotecaria"),
            ("sin tabla de criterios", todas, "falta la tabla de criterios", None),
            ("[PENDIENTE] sin pregunta", lambda t: con(t, "[PENDIENTE P-02]", "[PENDIENTE P-99]"),
             "P-99", "[PENDIENTE P-99]"),
            ("[RESUELTA] cita un ADR inexistente", lambda t: con(t, "[RESUELTA → ADR-0002]", "[RESUELTA → ADR-0099]"),
             "cita una decisión que no existe", "ADR-0099"),
            ("falta «Flujos principales»", lambda t: sin_linea(t, "### Flujos principales"),
             "falta «### Flujos principales»", "## Datos principales"),
            ("título principal mal escrito", lambda t: con(t, "# DISENO — Biblioteca de barrio", "# Diseño de la biblioteca"),
             "el título debe ser", "# Diseño de la biblioteca"),
            ("dos títulos principales", lambda t: con(t, "## Actores", "# Otro título\n\n## Actores"),
             "solo puede haber un título", "# Otro título"),
            ("texto antes del título", lambda t: "hola\n" + t, "hay texto antes del título", "hola"),
            ("archivo vacío", lambda t: "", "el archivo está vacío", 0),
        ]
        for nombre, estropear, mensaje, marca in casos:
            with self.subTest(nombre):
                texto = estropear(EJEMPLO)
                d = analizar(texto)
                if marca is None:
                    esperada = None
                elif marca == 0:
                    esperada = 0
                elif isinstance(marca, tuple):
                    esperada = linea_de(texto, marca[0], ultima=marca[1])
                else:
                    esperada = linea_de(texto, marca)
                self.assertTrue(tiene_error(d, mensaje, esperada),
                                f"esperaba el error «{mensaje}» en la línea {esperada}; salió: {d.errores}")

    def test_el_ejemplo_solo_trae_los_avisos_esperados(self):
        mensajes = [m for _, m in analizar(EJEMPLO).avisos]
        self.assertEqual(len(mensajes), 2)
        self.assertTrue(any("bloquean tareas" in m and "P-01" in m for m in mensajes))
        self.assertTrue(any("siguen en estado «propuesta»" in m for m in mensajes))

    def test_avisos_de_campos_sin_llenar_y_texto_suelto(self):
        d = analizar(con(EJEMPLO, "Una biblioteca de barrio presta", "«describe el problema» presta"))
        self.assertTrue(any("sin llenar" in m for _, m in d.avisos))
        d = analizar(con(EJEMPLO, "## Funcionalidades\n", "## Funcionalidades\n\nTexto que no es un requisito.\n"))
        self.assertEqual(d.errores, [])
        self.assertTrue(any("no está dentro de ningún requisito" in m for _, m in d.avisos))

    def test_los_bloques_de_codigo_y_comentarios_no_cuentan_como_titulos(self):
        t = con(EJEMPLO, "### Flujos principales\n",
                "### Flujos principales\n\n```text\n## Esto no es una sección\n### RF-009 · Tampoco\n```\n")
        t = con(t, "## Actores", "<!--\n## Falso\n### ADR-0009 · Falso\n-->\n\n## Actores")
        d = analizar(t)
        self.assertEqual(d.errores, [])
        modelo = dict(d.reparto())["docs/modelo.md"]
        self.assertIn("## Esto no es una sección", modelo)  # viaja tal cual, dentro del modelo


# ---- reparto --------------------------------------------------------------
class Reparto(unittest.TestCase):
    def test_nombres_de_archivo(self):
        rutas = [r for r, _ in analizar(EJEMPLO).reparto()]
        self.assertEqual(rutas, [
            "docs/requisitos/contexto.md",
            "docs/requisitos/RF-001-registrar-libro.md",
            "docs/requisitos/RF-002-prestar-libro.md",
            "docs/requisitos/RF-003-listar-atrasos.md",
            "docs/modelo.md",
            "docs/decisiones/0001-usar-una-base-de-datos-relacional.md",
            "docs/decisiones/0002-interfaz-web-sencilla-sin-app-movil.md",
        ])

    def test_se_reparte_tal_cual_sin_perder_ni_inventar_lineas(self):
        d = analizar(EJEMPLO)
        originales = Counter(l for l in EJEMPLO.splitlines() if l.strip())
        # Estas líneas no viajan tal cual a propósito: el título principal, los títulos de cada RF y ADR
        # (suben de nivel) y los dos contenedores, que no tienen contenido propio: sus requisitos y
        # decisiones se reparten uno por archivo.
        for l in [x for x in EJEMPLO.splitlines()
                  if x.startswith(("# DISENO", "### RF-", "### ADR-")) or x in ("## Funcionalidades", "## Decisiones")]:
            originales[l] -= 1
        repartidas = Counter(l for _, c in d.reparto() for l in c.splitlines() if l.strip())
        for l in [x for _, c in d.reparto() for x in c.splitlines()
                  if x.startswith(("# Contexto — ", "# Modelo — ", "# RF-", "# ADR-"))]:
            repartidas[l] -= 1  # y estos son los títulos nuevos
        self.assertEqual(+originales, +repartidas)

    def test_los_titulos_suben_de_nivel_y_el_contexto_conserva_el_orden(self):
        archivos = dict(analizar(EJEMPLO).reparto())
        self.assertTrue(archivos["docs/requisitos/RF-001-registrar-libro.md"].startswith("# RF-001 · Registrar libro\n"))
        self.assertTrue(archivos["docs/decisiones/0001-usar-una-base-de-datos-relacional.md"]
                        .startswith("# ADR-0001 · Usar una base de datos relacional\n"))
        contexto = archivos["docs/requisitos/contexto.md"]
        self.assertTrue(contexto.startswith("# Contexto — Biblioteca de barrio\n\n> Versión 1"))
        orden = [l[3:] for l in contexto.splitlines() if l.startswith("## ")]
        self.assertEqual(orden, TODAS_LAS_SECCIONES)
        for _, c in analizar(EJEMPLO).reparto():
            self.assertTrue(c.endswith("\n") and not c.endswith("\n\n"))

    def test_slug(self):
        self.assertEqual(idz.slug("Qué pasó con ñandú"), "que-paso-con-nandu")
        self.assertEqual(idz.slug("Usar Django 5.2 LTS"), "usar-django-5-2-lts")
        self.assertEqual(idz.slug("¡¡¡"), "sin-titulo")
        self.assertLessEqual(len(idz.slug("palabra " * 30)), 50)


# ---- línea de comandos ------------------------------------------------------
class LineaDeComandos(unittest.TestCase):
    def preparar(self, texto=EJEMPLO, nombre="DISENO.md", como_bytes=None):
        repo = RepoTemporal(self)
        (repo.dir / nombre).write_bytes(como_bytes if como_bytes is not None else texto.encode("utf-8"))
        return repo

    def test_check_no_escribe_nada(self):
        repo = self.preparar()
        antes = repo.archivos()
        r = repo.correr("DISENO.md", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no se escribió nada", r.stdout)
        self.assertEqual(repo.archivos(), antes)

    def test_el_resumen_concuerda_en_singular_y_plural(self):
        repo = self.preparar()
        self.assertIn("(3 requisitos, 2 decisiones, 3 criterios)", repo.correr("DISENO.md", "--check").stdout)
        uno = self.preparar(texto=PLANTILLA.read_text(encoding="utf-8")) if PLANTILLA.is_file() else None
        if uno:
            self.assertIn("(1 requisito, 1 decisión, 1 criterio)", uno.correr("DISENO.md", "--check").stdout)

    def test_reparte_y_mueve_el_original_desde_la_raiz(self):
        repo = self.preparar()
        r = repo.correr("DISENO.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(repo.archivos(), sorted([
            "tools/init_diseno.py", "docs/archivo/DISENO.md", "docs/modelo.md",
            "docs/requisitos/contexto.md", "docs/requisitos/RF-001-registrar-libro.md",
            "docs/requisitos/RF-002-prestar-libro.md", "docs/requisitos/RF-003-listar-atrasos.md",
            "docs/decisiones/0001-usar-una-base-de-datos-relacional.md",
            "docs/decisiones/0002-interfaz-web-sencilla-sin-app-movil.md"]))
        self.assertEqual((repo.dir / "docs/archivo/DISENO.md").read_bytes(), EJEMPLO.encode("utf-8"))
        self.assertIn("se movió desde la raíz", r.stdout)

    def test_no_pisa_archivos_existentes_salvo_con_force(self):
        repo = self.preparar()
        self.assertEqual(repo.correr("DISENO.md").returncode, 0)
        (repo.dir / "DISENO.md").write_text(EJEMPLO, encoding="utf-8")
        modelo = repo.dir / "docs/modelo.md"
        modelo.write_text("EDITADO A MANO\n", encoding="utf-8")
        r = repo.correr("DISENO.md")
        self.assertEqual(r.returncode, 2)
        self.assertIn("ya existen", r.stdout)
        self.assertEqual(modelo.read_text(encoding="utf-8"), "EDITADO A MANO\n")
        self.assertTrue((repo.dir / "DISENO.md").exists(), "si se negó, no debe borrar el original")
        r = repo.correr("DISENO.md", "--force")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotEqual(modelo.read_text(encoding="utf-8"), "EDITADO A MANO\n")

    def test_un_original_fuera_del_repo_no_se_toca(self):
        repo = RepoTemporal(self)
        fuera = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, fuera, True)
        origen = fuera / "DISENO.md"
        origen.write_text(EJEMPLO, encoding="utf-8")
        r = repo.correr(str(origen))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(origen.exists())
        self.assertIn("tu archivo original no se tocó", r.stdout)

    def test_con_errores_no_escribe_nada_y_sale_con_1(self):
        repo = self.preparar(texto=sin_linea(EJEMPLO, "## Actores"))
        antes = repo.archivos()
        r = repo.correr("DISENO.md")
        self.assertEqual(r.returncode, 1)
        self.assertIn("falta la sección «## Actores»", r.stdout)
        self.assertEqual(repo.archivos(), antes)

    def test_archivo_inexistente_sale_con_2(self):
        r = RepoTemporal(self).correr("NO-EXISTE.md")
        self.assertEqual(r.returncode, 2)
        self.assertIn("No encuentro el archivo", r.stdout)

    def test_no_acepta_el_propio_archivo_de_docs_archivo(self):
        repo = self.preparar()
        repo.correr("DISENO.md")
        r = repo.correr("docs/archivo/DISENO.md", "--force")
        self.assertEqual(r.returncode, 2)
        self.assertTrue((repo.dir / "docs/archivo/DISENO.md").exists())

    def test_archivo_que_no_es_utf8(self):
        repo = self.preparar(como_bytes=EJEMPLO.encode("latin-1", errors="replace"))
        r = repo.correr("DISENO.md")
        self.assertEqual(r.returncode, 1)
        self.assertIn("UTF-8", r.stdout)

    def test_bom_y_saltos_de_linea_de_windows_dan_el_mismo_reparto(self):
        limpio, windows = self.preparar(), self.preparar(
            como_bytes=b"\xef\xbb\xbf" + EJEMPLO.replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual(limpio.correr("DISENO.md").returncode, 0)
        r = windows.correr("DISENO.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for rel in [a for a in limpio.archivos() if a.startswith("docs/") and not a.startswith("docs/archivo/")]:
            self.assertEqual((limpio.dir / rel).read_bytes(), (windows.dir / rel).read_bytes(), rel)
            self.assertNotIn(b"\r", (windows.dir / rel).read_bytes(), f"{rel} debe quedar con saltos LF")

    def test_una_consola_sin_acentos_no_tumba_el_programa(self):
        repo = self.preparar()
        r = repo.correr("DISENO.md", "--check", env={"PYTHONIOENCODING": "ascii"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
