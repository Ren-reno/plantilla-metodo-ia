"""Pruebas de tools/init_plan.py. Solo usan la biblioteca estándar.

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
from unittest import mock

AQUI = Path(__file__).resolve().parent
TOOLS = AQUI.parent
sys.path.insert(0, str(TOOLS))
import init_plan as ip  # noqa: E402

EJEMPLO = (AQUI / "fixtures" / "PLAN-ejemplo.md").read_text(encoding="utf-8")
OLA2 = (AQUI / "fixtures" / "PLAN-ola2-ejemplo.md").read_text(encoding="utf-8")
DISENO = (AQUI / "fixtures" / "DISENO-ejemplo.md").read_text(encoding="utf-8")
PLANTILLA = TOOLS.parent / "docs" / "plantillas" / "plan.md"
RFS_DEL_EJEMPLO = {"RF-001", "RF-002", "RF-003"}
MINIMO = """# PLAN — Mini
> Versión 1 · 28-oct-2026 · fuente: DISENO.md, versión 1
## Backlog
### Rebanada 1 · Arranca
- T-001 · Esqueleto andante · Depende de: — · Cubre: C1 (5)
## Matriz de cobertura
| Criterio | RF | Tareas |
|---|---|---|
| C1 | RF-001 | T-001 |
## Tarjetas de la ola 1
### T-001 · Esqueleto andante
Estado: pendiente · Tamaño: S · Depende de: — · Cubre: C1 (5)
Objetivo: arrancar
"""


# ---- ayudas ---------------------------------------------------------------
def contexto(**kw):
    kw.setdefault("rfs", set(RFS_DEL_EJEMPLO))
    return ip.Contexto(**kw)


def contexto_con_backlog(texto=EJEMPLO, **kw):
    """El contexto de un repo donde ya se repartió ese plan (su backlog.md guardado)."""
    guardado = ip.leer_backlog_guardado(dict(ip.Plan(texto).analizar().reparto())[ip.REL_BACKLOG])
    return contexto(backlog=guardado, planes=[ip.REL_BACKLOG, ip.REL_COBERTURA], **kw)


def analizar(texto, ctx=None):
    return ip.Plan(texto).analizar(ctx or contexto())


def con(texto, viejo, nuevo):
    assert viejo in texto, f"la prueba está mal escrita: no encuentro {viejo!r}"
    return texto.replace(viejo, nuevo, 1)


def sin_linea(texto, fragmento):
    lineas = texto.split("\n")
    i = next(k for k, l in enumerate(lineas) if fragmento in l)
    return "\n".join(lineas[:i] + lineas[i + 1:])


def recortar(texto, desde, hasta):
    """Quita el texto que va desde «desde» hasta justo antes de «hasta»."""
    assert desde in texto and hasta in texto, "la prueba está mal escrita"
    i = texto.index(desde)
    return texto[:i] + texto[texto.index(hasta, i):]


def sin_lineas_que_empiezan_con(texto, prefijo):
    return "\n".join(l for l in texto.split("\n") if not l.startswith(prefijo))


def linea_de(texto, fragmento, ultima=False):
    numeros = [k + 1 for k, l in enumerate(texto.split("\n")) if fragmento in l]
    return numeros[-1] if ultima else numeros[0]


def tiene_error(p, mensaje, linea=None):
    return any(mensaje in m and (linea is None or n == linea) for n, m in p.errores)


def tiene_aviso(p, mensaje):
    return any(mensaje in m for _, m in p.avisos)


def v2(texto=EJEMPLO, motivo="se agrega la exportación de atrasos"):
    """El ejemplo convertido en una replanificación (versión 2) con una tarea nueva."""
    t = con(texto, "> Versión 1 ·", f"> Motivo del cambio: {motivo}\n> Versión 2 ·")
    t = con(t, "- T-005 · Buscar", "- T-006 · Exportar atrasos · Depende de: T-004 · Cubre: C2 (3), RF-003\n- T-005 · Buscar")
    return con(t, "| C2 | RF-003 | T-004 |", "| C2 | RF-003 | T-004, T-006 |")


class RepoTemporal:
    """Un repo de mentira con solo tools/init_diseno.py e init_plan.py, para probar la línea de comandos."""

    def __init__(self, test):
        self.dir = Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, self.dir, True)
        (self.dir / "tools").mkdir()
        for nombre in ("init_diseno.py", "init_plan.py"):
            shutil.copy(TOOLS / nombre, self.dir / "tools" / nombre)

    def correr(self, *args, env=None, herramienta="init_plan.py"):
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
        entorno.update(env or {})
        return subprocess.run([sys.executable, str(self.dir / "tools" / herramienta), *args],
                              cwd=self.dir, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=entorno)

    def archivos(self):
        return sorted(p.relative_to(self.dir).as_posix() for p in self.dir.rglob("*")
                      if p.is_file() and "__pycache__" not in p.parts)

    def leer(self, rel):
        return (self.dir / rel).read_text(encoding="utf-8")


# ---- formato --------------------------------------------------------------
class Formato(unittest.TestCase):
    def test_el_ejemplo_es_valido(self):
        p = analizar(EJEMPLO)
        self.assertEqual(p.errores, [])
        self.assertEqual((p.modo, p.ola, p.version, p.nombre), ("completo", 1, 1, "Biblioteca de barrio"))
        self.assertEqual(list(p.tareas), ["T-001", "T-002", "T-003", "T-004", "T-005"])
        self.assertEqual(sorted(p.rebanadas), [1, 2])
        self.assertEqual([t["id"] for t in p.tarjetas], ["T-001", "T-002", "T-003"])
        self.assertEqual(p.tareas["T-003"]["depende"], ["T-002"])
        self.assertEqual(p.tareas["T-003"]["cubre"], ["C1 (5)", "RF-002", "RN-01"])
        self.assertEqual(p.tareas["T-004"]["reb"], 2)

    def test_el_ejemplo_no_trae_avisos(self):
        self.assertEqual(analizar(EJEMPLO).avisos, [])

    @unittest.skipUnless(PLANTILLA.is_file(), "no está docs/plantillas/plan.md")
    def test_la_plantilla_de_plan_cumple_el_formato(self):
        p = analizar(PLANTILLA.read_text(encoding="utf-8"), ip.Contexto())
        self.assertEqual(p.errores, [], "la plantilla y el analizador deben estar de acuerdo")
        self.assertTrue(tiene_aviso(p, "sin llenar"))

    def test_las_olas_siguientes_solo_traen_tarjetas(self):
        p = analizar(OLA2, contexto_con_backlog())
        self.assertEqual(p.errores, [])
        self.assertEqual((p.modo, p.ola), ("tarjetas", 2))
        self.assertEqual(p.avisos, [])
        self.assertEqual([t["id"] for t in p.tarjetas], ["T-004", "T-005"])

    def test_una_ola_siguiente_acepta_titulo_y_cabecera_opcionales(self):
        p = analizar("# PLAN — Biblioteca de barrio\n> Ola 2 del plan versión 1\n\n" + OLA2, contexto_con_backlog())
        self.assertEqual(p.errores, [])
        self.assertEqual(p.modo, "tarjetas")

    def test_cada_error_se_detecta_con_su_linea(self):
        casos = [
            # (nombre, cómo se estropea el ejemplo, mensaje esperado, fragmento que marca la línea; 0 = sin línea)
            ("archivo vacío", lambda t: "", "el archivo está vacío", 0),
            ("falta el título principal", lambda t: sin_linea(t, "# PLAN —"),
             "falta el título «# PLAN — nombre de la app»", 0),
            ("título mal escrito", lambda t: con(t, "# PLAN — Biblioteca de barrio", "# Plan de la biblioteca"),
             "el título debe ser", "# Plan de la biblioteca"),
            ("dos títulos principales", lambda t: con(t, "## Backlog", "# Otro título\n\n## Backlog"),
             "solo puede haber un título", "# Otro título"),
            ("texto antes del título", lambda t: "hola\n" + t, "hay texto antes del título", "hola"),
            ("falta la línea de versión", lambda t: sin_linea(t, "> Versión 1"), "falta la línea «> Versión 1",
             "# PLAN —"),
            ("versión que no es un número", lambda t: con(t, "> Versión 1 ·", "> Versión uno ·"),
             "falta la línea «> Versión 1", "# PLAN —"),
            ("versión 2 sin motivo", lambda t: con(t, "> Versión 1 ·", "> Versión 2 ·"),
             "replanifica el backlog", "> Versión 2"),
            ("versión 2 con el motivo sin llenar",
             lambda t: con(t, "> Versión 1 ·", "> Motivo del cambio: «qué cambió»\n> Versión 2 ·"),
             "replanifica el backlog", "> Versión 2"),
            ("falta la matriz", lambda t: recortar(t, "## Matriz de cobertura", "## Tarjetas de la ola 1"),
             "van juntos: falta «## Matriz de cobertura»", 0),
            ("falta el backlog", lambda t: recortar(t, "## Backlog", "## Matriz de cobertura"),
             "van juntos: falta «## Backlog»", 0),
            ("faltan las tarjetas", lambda t: t[:t.index("## Tarjetas de la ola 1")],
             "falta la sección «## Tarjetas de la ola N»", 0),
            ("sección mal escrita", lambda t: con(t, "## Matriz de cobertura", "## Matriz de Cobertura"),
             "¿quisiste decir «Matriz de cobertura»?", "## Matriz de Cobertura"),
            ("ola sin número", lambda t: con(t, "## Tarjetas de la ola 1", "## Tarjetas de la ola"),
             "falta el número de la ola", "## Tarjetas de la ola"),
            ("backlog repetido",
             lambda t: t + "\n## Backlog\n- T-009 · X · Depende de: — · Cubre: C1 (5)\n",
             "está repetida", ("## Backlog", True)),
            ("dos olas en un archivo",
             lambda t: t + "\n## Tarjetas de la ola 2\n### T-004 · Listar atrasos\n",
             "solo puede haber una sección", ("## Tarjetas de la ola 2", False)),
            ("la ola no existe en el backlog", lambda t: con(t, "## Tarjetas de la ola 1", "## Tarjetas de la ola 7"),
             "la ola 7 no existe en el backlog", "## Tarjetas de la ola 7"),
            ("rebanada mal escrita", lambda t: con(t, "### Rebanada 2 · Revisar", "### Segunda · Revisar"),
             "las rebanadas se escriben", "### Segunda"),
            ("rebanada repetida", lambda t: con(t, "### Rebanada 2 ·", "### Rebanada 1 ·"),
             "la rebanada 1 está repetida", "### Rebanada 1 · Revisar"),
            ("tarea fuera de toda rebanada",
             lambda t: con(t, "## Backlog\n", "## Backlog\n- T-009 · Suelta · Depende de: — · Cubre: C1 (5)\n"),
             "no está dentro de ninguna rebanada", "- T-009"),
            ("tarea mal formada",
             lambda t: con(t, "- T-002 · Registrar libro · Depende de: T-001 ·", "- T-002 · Registrar libro ·"),
             "la tarea debe escribirse", "- T-002 · Registrar libro · Cubre"),
            ("título con el separador", lambda t: con(t, "Registrar libro · Depende", "Registrar · libro · Depende"),
             "no puede contener « · »", "- T-002"),
            ("ID de tarea repetido", lambda t: con(t, "- T-003 · Prestar", "- T-002 · Prestar"),
             "T-002 está repetida", "- T-002 · Prestar"),
            ("depende de una tarea que no existe",
             lambda t: con(t, "Depende de: T-002 · Cubre: C1 (5), RF-002", "Depende de: T-009 · Cubre: C1 (5), RF-002"),
             "depende de T-009, que no está en el backlog", "- T-003"),
            ("depende de sí misma",
             lambda t: con(t, "- T-002 · Registrar libro · Depende de: T-001", "- T-002 · Registrar libro · Depende de: T-002"),
             "no puede depender de sí misma", "- T-002"),
            ("«Depende de:» con algo que no es una tarea",
             lambda t: con(t, "Depende de: T-001 · Cubre: C1 (5), RF-001", "Depende de: la anterior · Cubre: C1 (5), RF-001"),
             "que no es una tarea", "- T-002"),
            ("«Cubre:» vacío", lambda t: con(t, "· Cubre: C1 (5), RF-001\n- T-003", "· Cubre:\n- T-003"),
             "no puede quedar vacío", "- T-002"),
            ("«Cubre:» con algo que no es criterio ni requisito",
             lambda t: con(t, "Cubre: C1 (5), RF-001\n- T-003", "Cubre: C1 (5), Z9\n- T-003"),
             "que no es un criterio", "- T-002"),
            ("backlog sin tareas", lambda t: sin_lineas_que_empiezan_con(t, "- T-"),
             "el backlog no tiene ninguna tarea", "## Backlog"),
            ("matriz sin tabla", lambda t: sin_lineas_que_empiezan_con(t, "|"),
             "falta la tabla de la matriz", "## Matriz de cobertura"),
            ("cabecera de la matriz distinta", lambda t: con(t, "| Criterio | RF | Tareas |", "| Criterio | Requisito | Tareas |"),
             "la cabecera de la tabla debe ser", "| Criterio | Requisito"),
            ("matriz sin filas",
             lambda t: sin_lineas_que_empiezan_con(sin_lineas_que_empiezan_con(sin_lineas_que_empiezan_con(t, "| C1 "), "| C2 "), "| C3 "),
             "la matriz no tiene ninguna fila", "| Criterio | RF | Tareas |"),
            ("fila de la matriz con pocas columnas", lambda t: con(t, "| C2 | RF-003 | T-004 |", "| C2 | T-004 |"),
             "la fila debe tener 3 columnas", "| C2 | T-004 |"),
            ("fila de la matriz que cita una tarea inexistente",
             lambda t: con(t, "| C3 | RF-001 | T-005 |", "| C3 | RF-001 | T-005, T-009 |"),
             "la fila cita T-009", "| C3 | RF-001 | T-005, T-009"),
            ("fila de la matriz con algo que no es una tarea",
             lambda t: con(t, "| C3 | RF-001 | T-005 |", "| C3 | RF-001 | tarea cinco |"),
             "no es una tarea", "tarea cinco"),
            ("tarjeta mal escrita", lambda t: con(t, "### T-002 · Registrar libro", "### Tarjeta dos"),
             "las tarjetas se escriben", "### Tarjeta dos"),
            ("tarjeta repetida", lambda t: con(t, "### T-002 · Registrar libro", "### T-001 · Registrar libro"),
             "T-001 está repetida", "### T-001 · Registrar libro"),
            ("tarjeta de una tarea que no está en el backlog",
             lambda t: con(t, "### T-002 · Registrar libro", "### T-009 · Registrar libro"),
             "no está en el backlog", "### T-009"),
            ("sin ninguna tarjeta", lambda t: t[:t.index("### T-001 · Esqueleto andante\nEstado")],
             "no hay ninguna tarjeta", "## Tarjetas de la ola 1"),
        ]
        for nombre, estropear, mensaje, marca in casos:
            with self.subTest(nombre):
                texto = estropear(EJEMPLO)
                p = analizar(texto)
                if marca is None:
                    esperada = None
                elif marca == 0:
                    esperada = 0
                elif isinstance(marca, tuple):
                    esperada = linea_de(texto, marca[0], ultima=marca[1])
                else:
                    esperada = linea_de(texto, marca)
                self.assertTrue(tiene_error(p, mensaje, esperada),
                                f"esperaba el error «{mensaje}» en la línea {esperada}; salió: {p.errores}")

    def test_una_tarea_dentro_de_una_rebanada_mal_escrita_no_llena_de_errores_en_cascada(self):
        p = analizar(con(EJEMPLO, "### Rebanada 2 · Revisar", "### Segunda · Revisar"))
        self.assertEqual(len(p.errores), 1, p.errores)

    def test_los_ref_nn_son_validos_van_a_su_archivo_y_no_se_comparan_con_el_backlog(self):
        ref = ("\n### REF-01 · Ordenar préstamos\nEstado: pendiente · Tamaño: S · Depende de: — · Cubre: —\n"
               "Objetivo: ordenar\n")
        p = analizar(EJEMPLO + ref)
        self.assertEqual((p.errores, p.avisos), ([], []))
        self.assertIn("docs/plan/tareas/REF-01.md", dict(p.reparto()))
        self.assertTrue(dict(p.reparto())["docs/plan/tareas/REF-01.md"].startswith("# REF-01 · Ordenar préstamos\n"))
        self.assertTrue(tiene_error(analizar(EJEMPLO + ref + ref), "REF-01 está repetida"))

    def test_los_decimales_dentro_de_parentesis_no_parten_el_cubre(self):
        self.assertEqual(ip._partir("C2 (2,5), RF-004"), ["C2 (2,5)", "RF-004"])
        p = analizar(con(EJEMPLO, "Cubre: C2 (3), RF-003\n", "Cubre: C2 (2,5), RF-003\n"))
        self.assertEqual(p.errores, [])
        self.assertEqual(p.tareas["T-004"]["cubre"], ["C2 (2,5)", "RF-003"])

    def test_los_bloques_de_codigo_y_comentarios_no_cuentan_como_titulos(self):
        t = con(EJEMPLO, "Objetivo: Poder registrar", "```text\n## Esto no es una sección\n### T-099 · Falsa\n```\nObjetivo: Poder registrar")
        t = con(t, "## Backlog", "<!--\n## Falso\n### T-098 · Falsa\n-->\n\n## Backlog")
        p = analizar(t)
        self.assertEqual(p.errores, [])
        self.assertIn("### T-099 · Falsa", dict(p.reparto())["docs/plan/tareas/T-002.md"])  # viaja tal cual

    def test_el_orden_y_los_espacios_no_importan_al_comparar_la_tarjeta_con_el_backlog(self):
        p = analizar(con(EJEMPLO, "Cubre: C1 (5), RF-001\nObjetivo: Poder", "Cubre: RF-001,  C1(5)\nObjetivo: Poder"))
        self.assertEqual((p.errores, p.avisos), ([], []))


# ---- avisos ---------------------------------------------------------------
class Avisos(unittest.TestCase):
    def test_cada_aviso_se_da_y_no_impide_repartir(self):
        tarjeta_t4 = ("\n### T-004 · Listar atrasos\nEstado: pendiente · Tamaño: S · Depende de: T-003 · "
                      "Cubre: C2 (3), RF-003\nObjetivo: x\n")
        casos = [
            # (nombre, cómo se estropea el ejemplo, contexto, mensaje esperado)
            ("la tarjeta ya existe", lambda t: t, contexto(tarjetas={"T-001"}),
             "T-001: ya existe docs/plan/tareas/T-001.md; no se pisa"),
            ("falta la tarjeta de una tarea de la ola",
             lambda t: t[:t.index("\n### T-003 · Prestar y devolver libro\nEstado")] + "\n", contexto(),
             "faltan las tarjetas de T-003 (rebanada 1)"),
            ("tarjeta de una tarea de otra ola", lambda t: t + tarjeta_t4, contexto(),
             "T-004 es de la rebanada 2 y esta es la ola 1"),
            ("«Depende de:» distinto al del backlog",
             lambda t: con(t, "Estado: pendiente · Tamaño: S · Depende de: T-001 ·", "Estado: pendiente · Tamaño: S · Depende de: T-003 ·"),
             contexto(), "«Depende de:» de la tarjeta (T-003) no coincide con el del backlog (T-001)"),
            ("«Cubre:» distinto al del backlog",
             lambda t: con(t, "Cubre: C1 (5), RF-001\nObjetivo: Poder", "Cubre: C1 (5)\nObjetivo: Poder"),
             contexto(), "«Cubre:» de la tarjeta (C1 (5)) no coincide con el del backlog (C1 (5), RF-001)"),
            ("la tarjeta no trae la línea «Estado:»",
             lambda t: con(t, "Estado: pendiente · Tamaño: S · Depende de: — · Cubre: C1 (5)\n", ""), contexto(),
             "la tarjeta no trae la línea «Estado:"),
            ("«Cubre: —» en el backlog", lambda t: con(t, "· Cubre: C1 (5)\n- T-002", "· Cubre: —\n- T-002"),
             contexto(), "T-001: no cubre ningún criterio ni requisito"),
            ("«Cubre:» cita requisitos sin archivo", lambda t: t, contexto(rfs={"RF-001"}),
             "sin archivo en docs/requisitos/: RF-002 (T-003), RF-003 (T-004)"),
            ("docs/requisitos está vacío", lambda t: t, contexto(rfs=set()), "no tiene ningún requisito"),
            ("tarjetas guardadas de tareas que ya no están", lambda t: t, contexto(tarjetas={"T-001", "T-014"}),
             "ya no están en el backlog nuevo: T-014"),
            ("campo de la plantilla sin llenar",
             lambda t: con(t, "Objetivo: Poder registrar un libro con título y autor y encontrarlo disponible.", "Objetivo: «describe»"),
             contexto(), "sin llenar"),
            ("texto suelto antes de las tarjetas",
             lambda t: con(t, "## Tarjetas de la ola 1\n", "## Tarjetas de la ola 1\n\nTexto que no es una tarjeta.\n"),
             contexto(), "no está dentro de ninguna tarjeta"),
        ]
        for nombre, estropear, ctx, mensaje in casos:
            with self.subTest(nombre):
                p = ip.Plan(estropear(EJEMPLO)).analizar(ctx)
                self.assertEqual(p.errores, [], p.errores)
                self.assertTrue(tiene_aviso(p, mensaje), f"esperaba el aviso «{mensaje}»; salió: {p.avisos}")

    def test_una_tarjeta_que_ya_existe_no_se_reparte(self):
        p = analizar(EJEMPLO, contexto(tarjetas={"T-001"}))
        rutas = [r for r, _ in p.reparto()]
        self.assertNotIn("docs/plan/tareas/T-001.md", rutas)
        self.assertIn("docs/plan/tareas/T-002.md", rutas)

    def test_una_tarjeta_guardada_cuenta_como_existente_al_buscar_las_que_faltan(self):
        sin_t3 = EJEMPLO[:EJEMPLO.index("\n### T-003 · Prestar y devolver libro\nEstado")] + "\n"
        p = ip.Plan(sin_t3).analizar(contexto(tarjetas={"T-003"}))
        self.assertFalse(tiene_aviso(p, "faltan las tarjetas"))


# ---- reparto --------------------------------------------------------------
class Reparto(unittest.TestCase):
    def test_nombres_de_archivo(self):
        self.assertEqual([r for r, _ in analizar(EJEMPLO).reparto()], [
            "docs/plan/backlog.md", "docs/plan/cobertura.md",
            "docs/plan/tareas/T-001.md", "docs/plan/tareas/T-002.md", "docs/plan/tareas/T-003.md"])

    def test_una_ola_siguiente_reparte_solo_tarjetas(self):
        rutas = [r for r, _ in analizar(OLA2, contexto_con_backlog()).reparto()]
        self.assertEqual(rutas, ["docs/plan/tareas/T-004.md", "docs/plan/tareas/T-005.md"])

    def test_se_reparte_tal_cual_sin_perder_ni_inventar_lineas(self):
        p = analizar(EJEMPLO)
        originales = Counter(l for l in EJEMPLO.splitlines() if l.strip())
        # Estas líneas no viajan tal cual a propósito: el título principal, el contenedor «## Backlog», el de las
        # tarjetas, las rebanadas (bajan de nivel) y el título de cada tarjeta (sube de nivel).
        for l in [x for x in EJEMPLO.splitlines()
                  if x.startswith(("# PLAN", "### Rebanada", "### T-")) or x in ("## Backlog", "## Tarjetas de la ola 1")]:
            originales[l] -= 1
        repartidas = Counter(l for _, c in p.reparto() for l in c.splitlines() if l.strip())
        for l in [x for _, c in p.reparto() for x in c.splitlines()
                  if x.startswith(("# Backlog — ", "# Cobertura — ", "## Rebanada ", "# T-"))]:
            repartidas[l] -= 1  # y estos son los títulos nuevos
        repartidas[next(l for l in EJEMPLO.splitlines() if l.startswith("> Versión"))] -= 1  # la línea de versión va en dos archivos
        self.assertEqual(+originales, +repartidas)

    def test_titulos_cabecera_y_niveles(self):
        archivos = dict(analizar(EJEMPLO).reparto())
        backlog, cobertura = archivos["docs/plan/backlog.md"], archivos["docs/plan/cobertura.md"]
        self.assertTrue(backlog.startswith("# Backlog — Biblioteca de barrio\n\n> Versión 1 ·"))
        self.assertIn("\n## Rebanada 1 · Prestar y devolver un libro de punta a punta\n- T-001 ·", backlog)
        self.assertNotIn("### Rebanada", backlog)
        self.assertNotIn("## Backlog", backlog)
        self.assertTrue(cobertura.startswith("# Cobertura — Biblioteca de barrio\n\n> Versión 1 ·"))
        self.assertIn("\n## Matriz de cobertura\n| Criterio | RF | Tareas |\n", cobertura)
        self.assertTrue(archivos["docs/plan/tareas/T-001.md"].startswith("# T-001 · Esqueleto andante\nEstado: pendiente"))
        for contenido in archivos.values():
            self.assertTrue(contenido.endswith("\n") and not contenido.endswith("\n\n"))

    def test_el_motivo_del_cambio_viaja_en_la_cabecera(self):
        archivos = dict(analizar(v2(), contexto_con_backlog()).reparto())
        for rel in ("docs/plan/backlog.md", "docs/plan/cobertura.md"):
            self.assertIn("> Motivo del cambio: se agrega la exportación de atrasos\n> Versión 2", archivos[rel])

    def test_el_backlog_guardado_se_lee_de_vuelta(self):
        g = ip.leer_backlog_guardado(dict(analizar(EJEMPLO).reparto())["docs/plan/backlog.md"])
        self.assertEqual(g.version, 1)
        self.assertEqual(list(g.tareas), ["T-001", "T-002", "T-003", "T-004", "T-005"])
        self.assertEqual(sorted(g.rebanadas), [1, 2])
        self.assertEqual([t for t, v in g.tareas.items() if v["reb"] == 2], ["T-004", "T-005"])

    def test_un_backlog_guardado_ilegible_se_dice_con_su_motivo(self):
        with self.assertRaisesRegex(ValueError, "Versión"):
            ip.leer_backlog_guardado("# Backlog — x\n\n## Rebanada 1 · a\n- T-001 · A · Depende de: — · Cubre: C1 (5)\n")
        with self.assertRaisesRegex(ValueError, "línea 5"):
            ip.leer_backlog_guardado("# Backlog — x\n\n> Versión 1 · fecha\n\n- T-001 · A · Depende de: — · Cubre: C1 (5)\n")
        with self.assertRaisesRegex(ValueError, "ninguna tarea"):
            ip.leer_backlog_guardado("# Backlog — x\n\n> Versión 1 · fecha\n\n## Rebanada 1 · a\n")


# ---- choques con lo que ya hay en el repo -------------------------------------
class Choques(unittest.TestCase):
    def test_el_primer_reparto_no_choca_con_nada(self):
        self.assertEqual(analizar(EJEMPLO).choques(contexto()), [])

    def test_repartir_dos_veces_el_mismo_plan_se_niega_salvo_con_force(self):
        ctx = contexto_con_backlog()
        self.assertTrue(any("ya es la versión 1" in c for c in analizar(EJEMPLO, ctx).choques(ctx)))
        self.assertEqual(analizar(EJEMPLO, ctx).choques(ctx, force=True), [])

    def test_la_replanificacion_valida_es_la_version_siguiente(self):
        ctx = contexto_con_backlog()
        self.assertEqual(analizar(v2(), ctx).choques(ctx), [])
        saltada = con(v2(), "> Versión 2 ·", "> Versión 3 ·")
        self.assertTrue(any("debe ser la 2" in c for c in analizar(saltada, ctx).choques(ctx)))

    def test_una_ola_siguiente_sin_backlog_guardado_no_se_puede_repartir(self):
        p = analizar(OLA2, contexto())
        self.assertTrue(any("no hay backlog guardado" in c for c in p.choques(contexto())))

    def test_un_backlog_guardado_que_no_se_puede_leer(self):
        ctx = contexto(error_backlog="no encuentro la línea «> Versión N · …»", planes=[ip.REL_BACKLOG])
        self.assertTrue(any("existe pero no se pudo leer" in c for c in analizar(OLA2, ctx).choques(ctx)))
        self.assertTrue(any("no pude leer la versión guardada" in c for c in analizar(EJEMPLO, ctx).choques(ctx)))
        self.assertEqual(analizar(EJEMPLO, ctx).choques(ctx, force=True), [])


# ---- escritura ------------------------------------------------------------
class Escritura(unittest.TestCase):
    def test_si_falla_a_medias_deja_todo_como_estaba(self):
        raiz = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, raiz, True)
        backlog = raiz / "docs" / "plan" / "backlog.md"
        backlog.parent.mkdir(parents=True)
        backlog.write_text("VIEJO\n", encoding="utf-8")
        origen = raiz / "PLAN-v2.md"
        origen.write_text(EJEMPLO, encoding="utf-8")
        archivo_orig = raiz / "docs" / "archivo" / "PLAN-v2.md"
        with mock.patch.object(ip.shutil, "copyfile", side_effect=OSError("disco lleno")):
            with self.assertRaises(OSError):
                ip._escribir(raiz, analizar(EJEMPLO).reparto(), origen, archivo_orig)
        self.assertEqual(backlog.read_text(encoding="utf-8"), "VIEJO\n", "lo que ya existía debe quedar como estaba")
        for rel in ("docs/plan/cobertura.md", "docs/plan/tareas/T-001.md", "docs/archivo/PLAN-v2.md"):
            self.assertFalse((raiz / rel).exists(), f"{rel} debía deshacerse")


# ---- línea de comandos ------------------------------------------------------
class LineaDeComandos(unittest.TestCase):
    def preparar(self, texto=EJEMPLO, nombre="PLAN.md", como_bytes=None):
        repo = RepoTemporal(self)
        self.poner(repo, texto, nombre, como_bytes)
        return repo

    @staticmethod
    def poner(repo, texto=EJEMPLO, nombre="PLAN.md", como_bytes=None):
        (repo.dir / nombre).write_bytes(como_bytes if como_bytes is not None else texto.encode("utf-8"))

    def repartido(self):
        """Un repo donde ya se repartió el PLAN.md de la ola 1."""
        repo = self.preparar()
        r = repo.correr("PLAN.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return repo

    def test_check_no_escribe_nada(self):
        repo = self.preparar()
        antes = repo.archivos()
        r = repo.correr("PLAN.md", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no se escribió nada", r.stdout)
        self.assertIn("Primer reparto del plan (versión 1)", r.stdout)
        self.assertEqual(repo.archivos(), antes)

    def test_el_resumen_concuerda_en_singular_y_plural(self):
        self.assertIn("(5 tareas en 2 rebanadas, 3 tarjetas)", self.preparar().correr("PLAN.md", "--check").stdout)
        self.assertIn("(1 tarea en 1 rebanada, 1 tarjeta)", self.preparar(MINIMO).correr("PLAN.md", "--check").stdout)
        repo = self.repartido()
        self.poner(repo, OLA2, "PLAN-ola2.md")
        self.assertIn("(ola 2: 2 tarjetas)", repo.correr("PLAN-ola2.md", "--check").stdout)

    def test_reparte_y_mueve_el_original_desde_la_raiz(self):
        repo = self.preparar()
        r = repo.correr("PLAN.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(repo.archivos(), sorted([
            "tools/init_diseno.py", "tools/init_plan.py", "docs/archivo/PLAN.md",
            "docs/plan/backlog.md", "docs/plan/cobertura.md",
            "docs/plan/tareas/T-001.md", "docs/plan/tareas/T-002.md", "docs/plan/tareas/T-003.md"]))
        self.assertEqual((repo.dir / "docs/archivo/PLAN.md").read_bytes(), EJEMPLO.encode("utf-8"))
        self.assertIn("se movió desde la raíz", r.stdout)

    def test_de_punta_a_punta_despues_de_init_diseno_no_hay_avisos(self):
        repo = RepoTemporal(self)
        (repo.dir / "DISENO.md").write_text(DISENO, encoding="utf-8")
        self.assertEqual(repo.correr("DISENO.md", herramienta="init_diseno.py").returncode, 0)
        self.poner(repo)
        r = repo.correr("PLAN.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Avisos", r.stdout)

    def test_las_olas_siguientes_reparten_solo_tarjetas(self):
        repo = self.repartido()
        backlog = (repo.dir / "docs/plan/backlog.md").read_bytes()
        self.poner(repo, OLA2, "PLAN-ola2.md")
        r = repo.correr("PLAN-ola2.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Solo tarjetas de la ola 2", r.stdout)
        for rel in ("docs/plan/tareas/T-004.md", "docs/plan/tareas/T-005.md", "docs/archivo/PLAN-ola2.md"):
            self.assertTrue((repo.dir / rel).is_file(), rel)
        self.assertEqual((repo.dir / "docs/plan/backlog.md").read_bytes(), backlog)

    def test_una_ola_siguiente_sin_backlog_guardado_sale_con_2(self):
        repo = self.preparar(OLA2, "PLAN-ola2.md")
        antes = repo.archivos()
        r = repo.correr("PLAN-ola2.md")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no hay backlog guardado", r.stdout)
        self.assertEqual(repo.archivos(), antes)

    def test_una_ola_que_no_existe_en_el_backlog_sale_con_1(self):
        repo = self.repartido()
        self.poner(repo, con(OLA2, "## Tarjetas de la ola 2", "## Tarjetas de la ola 3"), "PLAN-ola3.md")
        r = repo.correr("PLAN-ola3.md")
        self.assertEqual(r.returncode, 1)
        self.assertIn("la ola 3 no existe", r.stdout)

    def test_no_pisa_tarjetas_existentes_pero_si_crea_las_que_faltan(self):
        repo = self.repartido()
        (repo.dir / "docs/plan/tareas/T-001.md").write_text("EDITADO A MANO\n", encoding="utf-8")
        (repo.dir / "docs/plan/tareas/T-003.md").unlink()
        self.poner(repo, EJEMPLO[EJEMPLO.index("## Tarjetas de la ola 1"):], "PLAN-ola1-resto.md")
        r = repo.correr("PLAN-ola1-resto.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(repo.leer("docs/plan/tareas/T-001.md"), "EDITADO A MANO\n")
        self.assertTrue((repo.dir / "docs/plan/tareas/T-003.md").is_file(), "la que faltaba debe crearse")
        self.assertIn("T-001: ya existe docs/plan/tareas/T-001.md; no se pisa", r.stdout)

    def test_una_replanificacion_valida_reemplaza_backlog_y_matriz_sin_tocar_las_tarjetas(self):
        repo = self.repartido()
        tarjetas = {t: (repo.dir / f"docs/plan/tareas/{t}.md").read_bytes() for t in ("T-001", "T-002", "T-003")}
        self.poner(repo, v2(), "PLAN-v2.md")
        r = repo.correr("PLAN-v2.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Replanificación: versión 1 → 2", r.stdout)
        self.assertIn("Archivos reemplazados:", r.stdout)
        self.assertIn("- T-006 · Exportar atrasos", repo.leer("docs/plan/backlog.md"))
        self.assertIn("> Versión 2", repo.leer("docs/plan/backlog.md"))
        self.assertIn("| C2 | RF-003 | T-004, T-006 |", repo.leer("docs/plan/cobertura.md"))
        self.assertTrue((repo.dir / "docs/archivo/PLAN.md").is_file() and (repo.dir / "docs/archivo/PLAN-v2.md").is_file())
        for t, antes in tarjetas.items():
            self.assertEqual((repo.dir / f"docs/plan/tareas/{t}.md").read_bytes(), antes, t)

    def test_una_replanificacion_sin_motivo_sale_con_1(self):
        repo = self.repartido()
        self.poner(repo, con(EJEMPLO, "> Versión 1 ·", "> Versión 2 ·"), "PLAN-v2.md")
        r = repo.correr("PLAN-v2.md")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Motivo del cambio", r.stdout)

    def test_la_version_equivocada_sale_con_2(self):
        repo = self.repartido()
        antes = repo.leer("docs/plan/backlog.md")
        self.poner(repo, con(v2(), "> Versión 2 ·", "> Versión 3 ·"), "PLAN-v3.md")
        r = repo.correr("PLAN-v3.md")
        self.assertEqual(r.returncode, 2)
        self.assertIn("debe ser la 2", r.stdout)
        self.assertEqual(repo.leer("docs/plan/backlog.md"), antes)

    def test_el_mismo_plan_otra_vez_se_niega_y_force_reemplaza_sin_pisar_tarjetas(self):
        repo = self.repartido()
        (repo.dir / "docs/plan/tareas/T-001.md").write_text("EDITADO A MANO\n", encoding="utf-8")
        otra = con(EJEMPLO, "# PLAN — Biblioteca de barrio", "# PLAN — Biblioteca vecinal")
        self.poner(repo, otra, "PLAN-copia.md")
        r = repo.correr("PLAN-copia.md")
        self.assertEqual(r.returncode, 2)
        self.assertIn("ya está repartido", r.stdout)
        self.assertIn("Biblioteca de barrio", repo.leer("docs/plan/backlog.md"))
        r = repo.correr("PLAN-copia.md", "--force")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("# Backlog — Biblioteca vecinal", repo.leer("docs/plan/backlog.md"))
        self.assertEqual(repo.leer("docs/plan/tareas/T-001.md"), "EDITADO A MANO\n", "--force nunca pisa tarjetas")

    def test_un_plan_archivado_no_se_pisa_ni_con_force(self):
        repo = self.repartido()
        antes = repo.leer("docs/plan/backlog.md")
        self.poner(repo, v2(), "PLAN.md")  # mismo nombre que el del primer reparto
        for args in (("PLAN.md",), ("PLAN.md", "--force")):
            r = repo.correr(*args)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("docs/archivo/PLAN.md ya existe", r.stdout)
        self.assertEqual(repo.leer("docs/plan/backlog.md"), antes)
        self.assertEqual((repo.dir / "docs/archivo/PLAN.md").read_bytes(), EJEMPLO.encode("utf-8"))

    def test_check_dice_lo_que_reemplazaria_y_refleja_los_choques(self):
        repo = self.repartido()
        self.poner(repo, v2(), "PLAN-v2.md")
        antes = repo.archivos()
        r = repo.correr("PLAN-v2.md", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("(reemplaza el actual)", r.stdout)
        self.assertIn("No se tocarían 3 tarjeta(s) que ya existen", r.stdout)
        self.poner(repo, EJEMPLO, "PLAN-copia.md")
        r = repo.correr("PLAN-copia.md", "--check")
        self.assertEqual(r.returncode, 2)
        self.assertIn("ya está repartido", r.stdout)
        self.assertEqual(repo.archivos(), sorted(antes + ["PLAN-copia.md"]))

    def test_con_errores_no_escribe_nada_y_sale_con_1(self):
        repo = self.preparar(texto=sin_linea(EJEMPLO, "## Matriz de cobertura"))
        antes = repo.archivos()
        r = repo.correr("PLAN.md")
        self.assertEqual(r.returncode, 1)
        self.assertIn("van juntos: falta «## Matriz de cobertura»", r.stdout)
        self.assertEqual(repo.archivos(), antes)

    def test_archivo_inexistente_sale_con_2(self):
        r = RepoTemporal(self).correr("NO-EXISTE.md")
        self.assertEqual(r.returncode, 2)
        self.assertIn("No encuentro el archivo", r.stdout)

    def test_no_acepta_el_propio_archivo_de_docs_archivo(self):
        repo = self.repartido()
        r = repo.correr("docs/archivo/PLAN.md", "--force")
        self.assertEqual(r.returncode, 2)
        self.assertTrue((repo.dir / "docs/archivo/PLAN.md").exists())

    def test_un_original_fuera_del_repo_no_se_toca(self):
        repo = RepoTemporal(self)
        fuera = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, fuera, True)
        origen = fuera / "PLAN.md"
        origen.write_text(EJEMPLO, encoding="utf-8")
        r = repo.correr(str(origen))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(origen.exists())
        self.assertIn("tu archivo original no se tocó", r.stdout)

    def test_archivo_que_no_es_utf8(self):
        repo = self.preparar(como_bytes=EJEMPLO.encode("latin-1", errors="replace"))
        r = repo.correr("PLAN.md")
        self.assertEqual(r.returncode, 1)
        self.assertIn("UTF-8", r.stdout)

    def test_bom_y_saltos_de_linea_de_windows_dan_el_mismo_reparto(self):
        limpio, windows = self.preparar(), self.preparar(
            como_bytes=b"\xef\xbb\xbf" + EJEMPLO.replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual(limpio.correr("PLAN.md").returncode, 0)
        r = windows.correr("PLAN.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for rel in [a for a in limpio.archivos() if a.startswith("docs/plan/")]:
            self.assertEqual((limpio.dir / rel).read_bytes(), (windows.dir / rel).read_bytes(), rel)
            self.assertNotIn(b"\r", (windows.dir / rel).read_bytes(), f"{rel} debe quedar con saltos LF")

    def test_una_consola_sin_acentos_no_tumba_el_programa(self):
        repo = self.preparar()
        r = repo.correr("PLAN.md", "--check", env={"PYTHONIOENCODING": "ascii"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
