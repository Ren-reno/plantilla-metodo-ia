"""Pruebas de tools/validar.py. Solo usan la biblioteca estándar.

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

AQUI = Path(__file__).resolve().parent
TOOLS = AQUI.parent
sys.path.insert(0, str(TOOLS))

import init_diseno as idz  # noqa: E402
import init_plan as ip  # noqa: E402
import validar as va  # noqa: E402

DISENO_EJEMPLO = (AQUI / "fixtures" / "DISENO-ejemplo.md").read_text(encoding="utf-8")
PLAN_EJEMPLO = (AQUI / "fixtures" / "PLAN-ejemplo.md").read_text(encoding="utf-8")


class RepoTemporal:
    """Un repo de mentira para probar validar.py tanto como módulo como vía CLI."""

    def __init__(self, test):
        self.dir = Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, self.dir, True)
        (self.dir / "tools").mkdir()
        for nombre in ("init_diseno.py", "init_plan.py", "validar.py"):
            shutil.copy(TOOLS / nombre, self.dir / "tools" / nombre)

    def poner(self, rel: str, texto: str):
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8", newline="\n")

    def correr(self, *args, env=None):
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
        entorno.update(env or {})
        return subprocess.run([sys.executable, str(self.dir / "tools" / "validar.py"), *args],
                              cwd=self.dir, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=entorno)

    def poblar_ejemplo(self):
        """Reparte el diseño y el plan de ejemplo para tener un estado válido completo."""
        # Toda tarjeta cita las reglas, y sin ellas bundle.py se niega a armar el bundle:
        # un repo con tarjetas y sin este archivo no es un estado real del método.
        self.poner("docs/00-LEEME-IA.md", "# Reglas para cualquier LLM\n\nContenido de prueba.\n")
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
        self.poner("DISENO.md", DISENO_EJEMPLO)
        subprocess.run([sys.executable, str(self.dir / "tools" / "init_diseno.py"), "DISENO.md"],
                       cwd=self.dir, check=True, capture_output=True, text=True, encoding="utf-8", env=entorno)
        self.poner("PLAN.md", PLAN_EJEMPLO)
        subprocess.run([sys.executable, str(self.dir / "tools" / "init_plan.py"), "PLAN.md"],
                       cwd=self.dir, check=True, capture_output=True, text=True, encoding="utf-8", env=entorno)


def hay(lista, fragmento):
    return any(fragmento in x for x in lista)


# ---- Detección de ciclos --------------------------------------------------
class TestDeteccionCiclos(unittest.TestCase):
    def test_grafo_aciclico_retorna_vacio(self):
        grafo = {
            "T-001": [],
            "T-002": ["T-001"],
            "T-003": ["T-002"],
        }
        self.assertEqual(va.detectar_ciclos(grafo), [])

    def test_ciclo_directo_de_dos_nodos(self):
        grafo = {
            "T-001": ["T-002"],
            "T-002": ["T-001"],
        }
        ciclos = va.detectar_ciclos(grafo)
        self.assertTrue(len(ciclos) >= 1)
        self.assertIn("T-001", ciclos[0])
        self.assertIn("T-002", ciclos[0])

    def test_ciclo_triangular_de_tres_nodos(self):
        grafo = {
            "T-001": ["T-003"],
            "T-002": ["T-001"],
            "T-003": ["T-002"],
        }
        ciclos = va.detectar_ciclos(grafo)
        self.assertTrue(len(ciclos) >= 1)


# ---- Grafía real de una ruta ----------------------------------------------
class TestRutaReal(unittest.TestCase):
    def setUp(self):
        self.repo = RepoTemporal(self)
        self.repo.poner("docs/EXPERIENCIA.md", "# Experiencia\n")
        self.repo.poner("docs/sub/Modelo.md", "# Modelo\n")

    def test_la_grafia_exacta_se_devuelve_tal_cual(self):
        self.assertEqual(va.ruta_real(self.repo.dir, "docs/EXPERIENCIA.md"), "docs/EXPERIENCIA.md")
        self.assertEqual(va.ruta_real(self.repo.dir, "docs/sub/Modelo.md"), "docs/sub/Modelo.md")

    def test_otra_grafia_devuelve_la_del_disco(self):
        self.assertEqual(va.ruta_real(self.repo.dir, "docs/experiencia.md"), "docs/EXPERIENCIA.md")
        self.assertEqual(va.ruta_real(self.repo.dir, "DOCS/sub/modelo.MD"), "docs/sub/Modelo.md")

    def test_lo_que_no_existe_devuelve_none(self):
        self.assertIsNone(va.ruta_real(self.repo.dir, "docs/no-existe.md"))
        self.assertIsNone(va.ruta_real(self.repo.dir, "otra/carpeta/x.md"))

    def test_una_carpeta_tambien_se_resuelve(self):
        self.assertEqual(va.ruta_real(self.repo.dir, "docs/sub"), "docs/sub")


# ---- Validaciones de fondo ------------------------------------------------
class TestValidadorBase(unittest.TestCase):
    def setUp(self):
        self.repo = RepoTemporal(self)
        self.repo.poblar_ejemplo()
        self.val = va.Validador(self.repo.dir)
        ret = self.val.cargar()
        self.assertEqual(ret, 0)

    def test_ejemplo_original_es_completamente_valido(self):
        errores, avisos = self.val.validar()
        self.assertEqual(errores, [], f"Errores inesperados: {errores}")
        # Solo avisos informativos sobre ADRs en propuesta (lo normal antes de arrancar T-001)
        for a in avisos:
            self.assertTrue("propuesta" in a or "no existe" in a or "líneas" in a)

    def citar_en_tarjeta(self, ruta, tid="T-002"):
        """Deja la tarjeta citando solo las reglas y la ruta indicada."""
        p = self.repo.dir / f"docs/plan/tareas/{tid}.md"
        lineas = [f"Leer (solo esto): docs/00-LEEME-IA.md · {ruta}" if l.startswith("Leer")
                  else l for l in p.read_text(encoding="utf-8").splitlines()]
        p.write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="\n")
        val = va.Validador(self.repo.dir)
        val.cargar()
        return val.validar()

    def poner_peso(self, peso, tid="T-002"):
        """Añade (o reemplaza) la línea «Peso:» de una tarjeta y revalida."""
        p = self.repo.dir / f"docs/plan/tareas/{tid}.md"
        lineas = [l for l in p.read_text(encoding="utf-8").splitlines() if not l.startswith("Peso:")]
        i = next(n for n, l in enumerate(lineas) if l.startswith("Estado:"))
        lineas.insert(i + 1, f"Peso: {peso}")
        p.write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="\n")
        val = va.Validador(self.repo.dir)
        val.cargar()
        return val.validar()

    def test_dos_resultados_independientes_se_avisan(self):
        errores, avisos = self.poner_peso("2 resultados · 1 frontera · 0 decisiones nuevas")
        self.assertTrue(hay(avisos, "declara 2 resultados independientes"), avisos)
        self.assertEqual(errores, [], "es aviso: partir o conservar la tarea lo decide la persona")

    def test_un_solo_resultado_no_molesta(self):
        _errores, avisos = self.poner_peso("1 resultado · sin fronteras nuevas · 0 decisiones")
        self.assertFalse(hay(avisos, "resultados independientes"), avisos)

    def test_sin_peso_declarado_no_se_avisa_nada(self):
        # «Peso:» es opcional en esta versión: una tarjeta antigua sin él sigue valiendo.
        _errores, avisos = self.val.validar()
        self.assertFalse(hay(avisos, "resultados independientes"), avisos)

    def test_un_archivo_citado_que_no_existe_es_error_no_aviso(self):
        # bundle.py se niega a armar el bundle en este mismo caso: avisarlo aquí y dejar
        # pasar el CI solo retrasa el bloqueo hasta que alguien intenta trabajar.
        errores, avisos = self.citar_en_tarjeta("docs/no-existe.md")
        self.assertTrue(hay(errores, "no existe en el repo ni indica"), errores)
        self.assertFalse(hay(avisos, "docs/no-existe.md"))

    def test_una_grafia_distinta_es_error_aunque_windows_la_resuelva(self):
        # El caso real del piloto: ocho tarjetas citaban docs/experiencia.md con
        # docs/EXPERIENCIA.md versionado; Windows lo resolvía y el CI quedó verde.
        self.repo.poner("docs/EXPERIENCIA.md", "# Experiencia\n")
        errores, _ = self.citar_en_tarjeta("docs/experiencia.md")
        self.assertTrue(hay(errores, "el archivo versionado es «docs/EXPERIENCIA.md»"), errores)

    def test_la_grafia_correcta_no_molesta(self):
        self.repo.poner("docs/EXPERIENCIA.md", "# Experiencia\n")
        errores, _ = self.citar_en_tarjeta("docs/EXPERIENCIA.md")
        self.assertFalse(hay(errores, "EXPERIENCIA"), errores)

    def test_citar_una_decision_reemplazada_es_error(self):
        # bundle.py también se niega. A diferencia de «propuesta», aquí no hay nada
        # pendiente de decidir: la tarjeta cita una decisión sustituida (H-13).
        adr = sorted((self.repo.dir / "docs/decisiones").glob("0*.md"))[0]
        texto = adr.read_text(encoding="utf-8")
        adr.write_text(texto.replace("Estado: propuesta", "Estado: reemplazada")
                            .replace("Estado: aceptada", "Estado: reemplazada"),
                       encoding="utf-8", newline="\n")
        errores, _ = self.citar_en_tarjeta(f"docs/decisiones/{adr.name}")
        self.assertTrue(hay(errores, "está «reemplazada»"), errores)

    def test_una_decision_en_propuesta_sigue_siendo_solo_aviso(self):
        adr = sorted((self.repo.dir / "docs/decisiones").glob("0*.md"))[0]
        texto = adr.read_text(encoding="utf-8")
        adr.write_text(texto.replace("Estado: aceptada", "Estado: propuesta"),
                       encoding="utf-8", newline="\n")
        errores, avisos = self.citar_en_tarjeta(f"docs/decisiones/{adr.name}")
        self.assertFalse(hay(errores, adr.name), errores)
        self.assertTrue(hay(avisos, "«propuesta»"), avisos)

    def test_un_archivo_que_produce_otra_tarea_sigue_exento(self):
        errores, _ = self.citar_en_tarjeta("docs/contratos/futuro.md (lo produce T-001)")
        self.assertFalse(hay(errores, "futuro.md"), errores)

    def test_detecta_ciclo_en_backlog(self):
        # Modificar backlog para introducir T-001 -> T-003 y T-003 -> T-001
        bk_path = self.repo.dir / ip.REL_BACKLOG
        texto = bk_path.read_text(encoding="utf-8")
        texto = texto.replace("T-001 · Esqueleto andante · Depende de: —",
                              "T-001 · Esqueleto andante · Depende de: T-003")
        bk_path.write_text(texto, encoding="utf-8", newline="\n")

        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "Ciclo de dependencias detectado"))

    def test_detecta_auto_dependencia(self):
        bk_path = self.repo.dir / ip.REL_BACKLOG
        texto = bk_path.read_text(encoding="utf-8")
        texto = texto.replace("T-002 · Registrar libro · Depende de: T-001",
                              "T-002 · Registrar libro · Depende de: T-002")
        bk_path.write_text(texto, encoding="utf-8", newline="\n")

        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "T-002: depende de sí misma"))

    def test_detecta_dependencia_inexistente(self):
        bk_path = self.repo.dir / ip.REL_BACKLOG
        texto = bk_path.read_text(encoding="utf-8")
        texto = texto.replace("T-002 · Registrar libro · Depende de: T-001",
                              "T-002 · Registrar libro · Depende de: T-999")
        bk_path.write_text(texto, encoding="utf-8", newline="\n")

        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "T-002: depende de «T-999», que no existe en el backlog"))

    def test_detecta_rf_huerfano(self):
        # Crear un RF nuevo en docs/requisitos/ que ninguna tarea cubre
        self.repo.poner("docs/requisitos/RF-009-nuevo.md",
                        "# RF-009 · Funcionalidad huérfana\nAporta a: C1\n\n### Criterios de aceptación\n- Criterio 1\n")
        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "El requisito RF-009 («RF-009-nuevo.md») no está cubierto"))

    def test_detecta_criterio_huerfano(self):
        # Agregar un criterio C4 a contexto.md que ninguna tarea cubre
        ctx_path = self.repo.dir / "docs/requisitos/contexto.md"
        texto = ctx_path.read_text(encoding="utf-8")
        texto += "\n| C4 | Criterio sin cubrir | 2 | propio |\n"
        ctx_path.write_text(texto, encoding="utf-8", newline="\n")

        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "El criterio de éxito C4 (de docs/requisitos/contexto.md) no está cubierto"))

    def test_detecta_tarjeta_con_mas_de_4_criterios(self):
        # Editar T-001 para ponerle 5 criterios
        t_path = self.repo.dir / "docs/plan/tareas/T-001.md"
        texto = t_path.read_text(encoding="utf-8")
        criterios_5 = (
            "Criterios de aceptación (→ tests):\n"
            "  - Criterio 1\n"
            "  - Criterio 2\n"
            "  - Criterio 3\n"
            "  - Criterio 4\n"
            "  - Criterio 5\n"
        )
        texto = texto.replace("Criterios de aceptación (→ tests):\n  - La app arranca y responde en la página de inicio\n  - Un test de humo pasa en local\n  - [verifica: CI] El CI corre ese test y sale en verde\n", criterios_5)
        t_path.write_text(texto, encoding="utf-8", newline="\n")

        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "T-001: tiene 5 criterios de aceptación (el arnés fija un máximo de 4; D16)"))

    def test_detecta_tarjeta_sin_fuera_de_alcance(self):
        t_path = self.repo.dir / "docs/plan/tareas/T-001.md"
        texto = t_path.read_text(encoding="utf-8")
        texto = texto.replace("Fuera de alcance: libros, socios y préstamos · inicio de sesión",
                              "Fuera de alcance: —")
        t_path.write_text(texto, encoding="utf-8", newline="\n")

        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "T-001: falta el campo «Fuera de alcance:»"))

    def _fuera_de_alcance(self, valor):
        """Reescribe «Fuera de alcance:» de T-001 y devuelve los errores de la validación."""
        t_path = self.repo.dir / "docs/plan/tareas/T-001.md"
        texto = t_path.read_text(encoding="utf-8")
        texto = texto.replace("Fuera de alcance: libros, socios y préstamos · inicio de sesión",
                              f"Fuera de alcance: {valor}")
        t_path.write_text(texto, encoding="utf-8", newline="\n")
        val = va.Validador(self.repo.dir)
        val.cargar()
        return val.validar()[0]

    def test_avisa_si_un_criterio_cita_una_regla_que_no_existe(self):
        # Del ensayo del perfil chat-web: una tarjeta exigia cumplir una regla cuyo texto no viajaba.
        t_path = self.repo.dir / "docs/plan/tareas/T-001.md"
        texto = t_path.read_text(encoding="utf-8")
        texto = texto.replace("  - Un test de humo pasa en local",
                              "  - Un test de humo pasa en local y cumple RN-09")
        t_path.write_text(texto, encoding="utf-8", newline="\n")
        val = va.Validador(self.repo.dir)
        val.cargar()
        _, avisos = val.validar()
        self.assertTrue(hay(avisos, "T-001: un criterio cita RN-09"), f"salio: {avisos}")

    def test_un_fuera_de_alcance_que_cita_entre_comillas_vale(self):
        # Del ensayo del perfil chat-web: «» es la comilla española, no solo la marca de un hueco.
        errores = self._fuera_de_alcance("la «vista previa» de un libro · inicio de sesión")
        self.assertFalse(hay(errores, "falta el campo «Fuera de alcance:»"), f"salió: {errores}")

    def test_el_hueco_de_la_plantilla_en_fuera_de_alcance_sigue_siendo_error(self):
        errores = self._fuera_de_alcance("«lo que NO se construye en esta tarea, aunque parezca razonable»")
        self.assertTrue(hay(errores, "T-001: falta el campo «Fuera de alcance:»"), f"salió: {errores}")

    def test_detecta_incoherencia_depende_entre_tarjeta_y_backlog(self):
        t_path = self.repo.dir / "docs/plan/tareas/T-002.md"
        texto = t_path.read_text(encoding="utf-8")
        texto = texto.replace("Depende de: T-001", "Depende de: T-003")
        t_path.write_text(texto, encoding="utf-8", newline="\n")

        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "T-002: «Depende de:» en la tarjeta (T-003) no coincide con el backlog (T-001)"))

    def test_detecta_incoherencia_cubre_entre_tarjeta_y_backlog(self):
        t_path = self.repo.dir / "docs/plan/tareas/T-002.md"
        texto = t_path.read_text(encoding="utf-8")
        texto = texto.replace("Cubre: C1 (5), RF-001", "Cubre: C2 (3), RF-003")
        t_path.write_text(texto, encoding="utf-8", newline="\n")

        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "T-002: «Cubre:» en la tarjeta"))

    def test_detecta_tarjeta_huerfana_en_tareas(self):
        # Crear T-099.md que no existe en el backlog
        self.repo.poner("docs/plan/tareas/T-099.md",
                        "# T-099 · Inexistente\nEstado: pendiente · Tamaño: S · Depende de: — · Cubre: C1\n"
                        "Fuera de alcance: nada\nCriterios de aceptación (→ tests):\n  - crit 1\n")
        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "T-099: la tarjeta existe en docs/plan/tareas/, pero la tarea no está en el backlog"))

    def test_tarjeta_refactor_valida(self):
        self.repo.poner("docs/plan/tareas/REF-01.md",
                        "# REF-01 · Ordenar módulos\nEstado: pendiente · Tamaño: S · Depende de: — · Cubre: —\n"
                        "Fuera de alcance: cambiar comportamiento\nTocar: src/libros/*\n"
                        "Criterios de aceptación (→ tests):\n  - Los tests no cambian y siguen verdes.\n")
        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        # No debe reportar que REF-01 falta en el backlog
        self.assertFalse(hay(errores, "REF-01: la tarjeta existe en docs/plan/tareas/, pero la tarea no está en el backlog"))

    def test_tarjeta_refactor_error_si_toca_tests_o_docs(self):
        self.repo.poner("docs/plan/tareas/REF-02.md",
                        "# REF-02 · Refactor indebido\nEstado: pendiente · Tamaño: S · Depende de: — · Cubre: —\n"
                        "Fuera de alcance: nada\nTocar: tests/libros/test_libros.py\n"
                        "Criterios de aceptación (→ tests):\n  - Los tests siguen verdes.\n")
        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "es una tarjeta de refactor (REF), pero «Tocar:» incluye «tests/libros/test_libros.py»"))

    def test_matriz_cobertura_falta_tarea(self):
        # Borrar T-002 de la matriz en docs/plan/cobertura.md
        mat_path = self.repo.dir / ip.REL_COBERTURA
        texto = mat_path.read_text(encoding="utf-8")
        texto = texto.replace("| C1 | RF-001 | T-001, T-002 |", "| C1 | RF-001 | T-001 |")
        mat_path.write_text(texto, encoding="utf-8", newline="\n")

        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "falta reflejar que T-002 cubre C1 | RF-001"))

    def test_matriz_cobertura_tarea_inexistente(self):
        mat_path = self.repo.dir / ip.REL_COBERTURA
        texto = mat_path.read_text(encoding="utf-8")
        texto = texto.replace("| C1 | RF-001 | T-001, T-002 |", "| C1 | RF-001 | T-001, T-002, T-999 |")
        mat_path.write_text(texto, encoding="utf-8", newline="\n")

        val = va.Validador(self.repo.dir)
        val.cargar()
        errores, _ = val.validar()
        self.assertTrue(hay(errores, "la fila C1 | RF-001 cita «T-999», que no está en el backlog"))

    def test_aviso_archivo_codigo_muy_grande(self):
        # Crear un archivo de más de 500 líneas en src/
        codigo_largo = "# Archivo largo\n" + ("x = 1\n" * 520)
        self.repo.poner("src/libros/pesado.py", codigo_largo)

        val = va.Validador(self.repo.dir)
        val.cargar()
        _, avisos = val.validar()
        self.assertTrue(hay(avisos, "src/libros/pesado.py tiene 521 líneas (supera 500 líneas)"))


# ---- CLI y Códigos de Salida ---------------------------------------------
class TarjetasDeUnCambio(unittest.TestCase):
    """D-05 del ensayo de entrega: el camino «cambio» de la guia deja la traza «que tarea cubre que» en
    su mini-diseno y no en el backlog, para que una funcionalidad de una pagina no obligue a
    replanificar. validar.py exigia la linea de backlog, asi que seguir la guia producia un error que
    bloquea el CI. Ahora busca la traza donde la guia dice que vive, sin dejar de exigirla."""

    CAMBIO = """# CAM-0001 · Historial de ejemplo
> 2026-11-07 · app de prueba

## Que se cambia
La app guarda algo.

## Tarjetas
- T-050
"""

    TARJETA = """# T-050 · Tarjeta de un cambio
Estado: pendiente · Depende de: — · Cubre: RF-001
Peso: 1 resultado · sin fronteras nuevas · 0 decisiones · sin preparacion de entorno
Objetivo: la que sale del mini-diseno de un cambio.
Leer (solo esto): docs/00-LEEME-IA.md · docs/cambios/0001-historial-de-ejemplo.md
Tocar: src/libros/*
Fuera de alcance: todo lo demas
Criterios de aceptación:
  - Hace lo suyo; evidencia: test.
Comando de test: ver docs/00-LEEME-IA.md
Entrega: un parche (git diff) + reporte + comandos para aplicar
"""

    def setUp(self):
        self.repo = RepoTemporal(self)
        self.repo.poblar_ejemplo()
        self.repo.poner("docs/plan/tareas/T-050.md", self.TARJETA)

    def errores(self):
        val = va.Validador(self.repo.dir)
        val.cargar()
        return val.validar()[0]

    def test_una_tarjeta_que_su_mini_diseno_lista_no_necesita_el_backlog(self):
        self.repo.poner("docs/cambios/0001-historial-de-ejemplo.md", self.CAMBIO)
        self.assertFalse(hay(self.errores(), "T-050"), f"salio: {self.errores()}")

    def test_si_el_mini_diseno_no_la_lista_sigue_siendo_huerfana(self):
        self.repo.poner("docs/cambios/0001-historial-de-ejemplo.md",
                        self.CAMBIO.replace("- T-050", "- T-999"))
        self.assertTrue(hay(self.errores(), "T-050: la tarjeta existe"), f"salio: {self.errores()}")

    def test_si_el_mini_diseno_no_existe_sigue_siendo_huerfana(self):
        self.assertTrue(hay(self.errores(), "T-050: la tarjeta existe"), f"salio: {self.errores()}")

    def test_una_tarjeta_sin_citar_ningun_cambio_sigue_siendo_huerfana(self):
        self.repo.poner("docs/cambios/0001-historial-de-ejemplo.md", self.CAMBIO)
        self.repo.poner("docs/plan/tareas/T-050.md",
                        self.TARJETA.replace(" · docs/cambios/0001-historial-de-ejemplo.md", ""))
        self.assertTrue(hay(self.errores(), "T-050: la tarjeta existe"), f"salio: {self.errores()}")

    RF_DEL_CAMBIO = """# RF-050 · Requisito que crea un cambio
Aporta a: C1
Criterios de aceptación:
- Hace lo suyo; evidencia: test.
"""

    def test_un_rf_que_solo_cubre_la_tarjeta_de_un_cambio_no_es_huerfano(self):
        # La otra puerta del mismo problema: el camino «cambio» crea un RF, y el bucle de cobertura
        # solo miraba las tareas del backlog, asi que ese RF parecia huerfano y el error bloqueaba igual.
        self.repo.poner("docs/cambios/0001-historial-de-ejemplo.md", self.CAMBIO)
        self.repo.poner("docs/requisitos/RF-050-de-un-cambio.md", self.RF_DEL_CAMBIO)
        self.repo.poner("docs/plan/tareas/T-050.md", self.TARJETA.replace("Cubre: RF-001", "Cubre: RF-050"))
        self.assertFalse(hay(self.errores(), "RF-050"), f"salio: {self.errores()}")

    def test_un_rf_sin_nadie_que_lo_cubra_sigue_siendo_huerfano(self):
        self.repo.poner("docs/cambios/0001-historial-de-ejemplo.md", self.CAMBIO)
        self.repo.poner("docs/requisitos/RF-050-de-un-cambio.md", self.RF_DEL_CAMBIO)
        self.assertTrue(hay(self.errores(), "RF-050"), f"salio: {self.errores()}")

    def test_el_nombre_de_la_tarea_no_se_confunde_con_otro_mas_largo(self):
        # «- T-0501» en la seccion Tarjetas no vale como traza de T-050.
        self.repo.poner("docs/cambios/0001-historial-de-ejemplo.md",
                        self.CAMBIO.replace("- T-050", "- T-0501"))
        self.assertTrue(hay(self.errores(), "T-050: la tarjeta existe"), f"salio: {self.errores()}")


class TestLineaDeComandos(unittest.TestCase):
    def setUp(self):
        self.repo = RepoTemporal(self)

    def test_salida_2_si_falta_docs(self):
        r = self.repo.correr()
        self.assertEqual(r.returncode, 2)
        self.assertIn("No encuentro la carpeta «docs/»", r.stdout)

    def test_salida_2_si_falta_backlog(self):
        (self.repo.dir / "docs").mkdir()
        r = self.repo.correr()
        self.assertEqual(r.returncode, 2)
        self.assertIn("El plan no ha sido repartido todavía", r.stdout)

    def test_salida_0_con_ejemplo_repartido(self):
        self.repo.poblar_ejemplo()
        r = self.repo.correr()
        self.assertEqual(r.returncode, 0)
        self.assertIn("Validación exitosa", r.stdout)

    def test_salida_1_si_hay_errores(self):
        self.repo.poblar_ejemplo()
        # Agregar un ciclo
        bk = self.repo.dir / ip.REL_BACKLOG
        t = bk.read_text(encoding="utf-8").replace("Depende de: —", "Depende de: T-002")
        bk.write_text(t, encoding="utf-8", newline="\n")

        r = self.repo.correr()
        self.assertEqual(r.returncode, 1)
        self.assertIn("Validación fallida:", r.stdout)
        self.assertIn("error(es)", r.stdout)

    def test_estricto_falla_si_hay_avisos(self):
        self.repo.poblar_ejemplo()
        # El ejemplo tiene avisos porque ADR-0001 está en propuesta
        r = self.repo.correr("--estricto")
        self.assertEqual(r.returncode, 1)
        self.assertIn("tratados como error (--estricto)", r.stdout)

    def test_codificacion_utf8_estatica(self):
        """Verifica que validar.py declara encoding en todas sus llamadas según D45."""
        arbol = ast.parse((TOOLS / "validar.py").read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            f = nodo.func
            llamada = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
            claves = {k.arg for k in nodo.keywords}
            binario = (llamada == "open" and len(nodo.args) > 1 and isinstance(nodo.args[1], ast.Constant)
                       and "b" in str(nodo.args[1].value))
            if llamada in ("read_text", "write_text") or (llamada == "open" and not binario):
                self.assertIn("encoding", claves, f"validar.py:{nodo.lineno}: {llamada}() sin encoding")
            if llamada == "open" and not binario and len(nodo.args) > 1 and "w" in str(getattr(nodo.args[1], "value", "")):
                self.assertIn("newline", claves, f"validar.py:{nodo.lineno}: open(..., 'w') sin newline")
            if llamada == "run" and "text" in claves:
                self.assertIn("encoding", claves, f"validar.py:{nodo.lineno}: subprocess.run(text=True) sin encoding")


if __name__ == "__main__":
    unittest.main()
