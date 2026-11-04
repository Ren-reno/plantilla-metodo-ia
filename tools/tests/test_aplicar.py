"""Pruebas de tools/aplicar.py. Solo usan la biblioteca estándar (unittest) y repos temporales.

Cada prueba que necesita git arma su propio repo en una carpeta temporal, con un HOME aislado (su propio
~/.metodo-ia.json y su carpeta Downloads) y sin la configuración de git de quien corre las pruebas.
El modo estricto se prueba con unittest y con muestras de la salida real de pytest (no hace falta tener pytest).
"""
import ast
import contextlib
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))
import aplicar as ap  # noqa: E402

FUENTE = TOOLS / "aplicar.py"
HAY_GIT = shutil.which("git") is not None

# ---- parches y archivos de ejemplo ---------------------------------------------------------------------
ARCHIVO_A = "uno\ndos\ntres\ncuatro\ncinco\n"
ARCHIVO_A_DESPUES = "uno\ndos\ntres\nCUATRO\ncinco\n"
PARCHE_A = (
    "diff --git a/a.txt b/a.txt\n"
    "--- a/a.txt\n"
    "+++ b/a.txt\n"
    "@@ -1,5 +1,5 @@\n"
    " uno\n"
    " dos\n"
    " tres\n"
    "-cuatro\n"
    "+CUATRO\n"
    " cinco\n"
)
PARCHE_B = (
    "diff --git a/b.txt b/b.txt\n"
    "--- a/b.txt\n"
    "+++ b/b.txt\n"
    "@@ -1,2 +1,2 @@\n"
    " x\n"
    "-y\n"
    "+Y\n"
)
PARCHE_MD = (  # un parche a un .md: sus líneas de contexto pueden ser vallas de código
    "diff --git a/guia.md b/guia.md\n"
    "--- a/guia.md\n"
    "+++ b/guia.md\n"
    "@@ -1,4 +1,6 @@\n"
    " # Guía\n"
    " ```powershell\n"
    " dir\n"
    "+cls\n"
    " ```\n"
    "+```text\n"
    "+fin\n"
)
PARCHE_ROTO = (  # a la cabecera del bloque le falta el «@@» de cierre: git dice «corrupt patch»
    "diff --git a/a.txt b/a.txt\n"
    "--- a/a.txt\n"
    "+++ b/a.txt\n"
    "@@ -1,3 +1,3\n"
    " uno\n"
    "-dos\n"
    "+DOS\n"
    " tres\n"
)

CALC_ESQUELETO = 'def sumar(a, b):\n    raise NotImplementedError("sumar")\n'
CALC_CERO = "def sumar(a, b):\n    return 0\n"
CALC_BIEN = "def sumar(a, b):\n    return a + b\n"
TEST_CALC = (
    "import unittest\n"
    "from calc import sumar\n"
    "\n"
    "\n"
    "class PruebaSumar(unittest.TestCase):\n"
    "    def test_suma(self):\n"
    "        self.assertEqual(sumar(1, 2), 3)\n"
)
COMANDO_UNITTEST = '"%s" -m unittest test_calc' % sys.executable


def parche_archivo_nuevo(nombre, contenido):
    lineas = contenido.split("\n")
    if lineas[-1] == "":
        lineas.pop()
    return ("diff --git a/%s b/%s\nnew file mode 100644\n--- /dev/null\n+++ b/%s\n@@ -0,0 +1,%d @@\n"
            % (nombre, nombre, nombre, len(lineas))) + "".join("+" + l + "\n" for l in lineas)


# ---- muestras de salida de pytest 9.2 y unittest (Python 3.12), recortadas de ruido -----------------------
SALIDA_PYTEST_NOT_IMPLEMENTED = """\
F                                                                        [100%]
=================================== FAILURES ===================================
__________________________________ test_sumar __________________________________

    def test_sumar():
>       assert sumar(1, 2) == 3
               ^^^^^^^^^^^

test_calc.py:3:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

a = 1, b = 2

    def sumar(a, b):
>       raise NotImplementedError("sumar")
E       NotImplementedError: sumar

calc.py:2: NotImplementedError
=========================== short test summary info ============================
FAILED test_calc.py::test_sumar - NotImplementedError: sumar
1 failed in 0.02s
"""
SALIDA_PYTEST_ASSERT = """\
F                                                                        [100%]
=================================== FAILURES ===================================
_________________________________ test_simple __________________________________

    def test_simple():
>       assert 1 + 1 == 3
E       assert (1 + 1) == 3

test_assert_simple.py:2: AssertionError
=========================== short test summary info ============================
FAILED test_assert_simple.py::test_simple - assert (1 + 1) == 3
1 failed in 0.02s
"""
SALIDA_PYTEST_ASSERT_TB_NO = """\
F                                                                        [100%]
=========================== short test summary info ============================
FAILED test_assert_simple.py::test_simple - assert (1 + 1) == 3
1 failed in 0.01s
"""
SALIDA_PYTEST_IMPORT_ERROR = """\

==================================== ERRORS ====================================
_____________________ ERROR collecting test_import_malo.py _____________________
ImportError while importing test module '/tmp/rojo/test_import_malo.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
test_import_malo.py:1: in <module>
    from calc import no_existe
E   ImportError: cannot import name 'no_existe' from 'calc' (/tmp/rojo/calc.py)
=========================== short test summary info ============================
ERROR test_import_malo.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.09s
"""
SALIDA_PYTEST_MODULE_NOT_FOUND = """\

==================================== ERRORS ====================================
_____________________ ERROR collecting test_modulo_malo.py _____________________
ImportError while importing test module '/tmp/rojo/test_modulo_malo.py'.
Traceback:
test_modulo_malo.py:1: in <module>
    import modulo_que_no_existe
E   ModuleNotFoundError: No module named 'modulo_que_no_existe'
=========================== short test summary info ============================
ERROR test_modulo_malo.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.11s
"""
SALIDA_PYTEST_SINTAXIS = """\

==================================== ERRORS ====================================
____________________ ERROR collecting test_sintaxis_malo.py ____________________
/usr/lib/python3.12/ast.py:52: in parse
    return compile(source, filename, mode, flags,
E     File "/tmp/rojo/test_sintaxis_malo.py", line 1
E       def test_x(:
E                  ^
E   SyntaxError: invalid syntax
=========================== short test summary info ============================
ERROR test_sintaxis_malo.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.21s
"""
SALIDA_PYTEST_NAME_ERROR = """\
F                                                                        [100%]
=================================== FAILURES ===================================
____________________________________ test_x ____________________________________

    def test_x():
>       assert variable_inexistente == 1
               ^^^^^^^^^^^^^^^^^^^^
E       NameError: name 'variable_inexistente' is not defined

test_nombre_malo.py:2: NameError
=========================== short test summary info ============================
FAILED test_nombre_malo.py::test_x - NameError: name 'variable_inexistente' i...
1 failed in 0.02s
"""
SALIDA_PYTEST_NAME_ERROR_TB_NO = """\
F                                                                        [100%]
=========================== short test summary info ============================
FAILED test_nombre_malo.py::test_x - NameError: name 'variable_inexistente' i...
1 failed in 0.01s
"""
SALIDA_PYTEST_NAME_ERROR_TB_LINE = """\
F                                                                        [100%]
=================================== FAILURES ===================================
/tmp/rojo/test_nombre_malo.py:2: NameError: name 'variable_inexistente' is not defined
=========================== short test summary info ============================
1 failed in 0.01s
"""
SALIDA_PYTEST_SIN_TESTS = """\
ERROR: file or directory not found: no_existe_xyz.py

no tests ran in 0.00s
"""
SALIDA_UNITTEST_MIXTA = """\
EF
======================================================================
ERROR: test_a (test_u.T.test_a)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/rojo/test_u.py", line 5, in test_a
    self.assertEqual(sumar(1,2),3)
  File "/tmp/rojo/calc.py", line 2, in sumar
    raise NotImplementedError("sumar")
NotImplementedError: sumar

======================================================================
FAIL: test_b (test_u.T.test_b)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/rojo/test_u.py", line 7, in test_b
    self.assertEqual(1+1,3)
AssertionError: 2 != 3

----------------------------------------------------------------------
Ran 2 tests in 0.001s

FAILED (failures=1, errors=1)
"""
SALIDA_UNITTEST_IMPORT = """\
E
======================================================================
ERROR: test_u_imp (unittest.loader._FailedTest.test_u_imp)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_u_imp
Traceback (most recent call last):
  File "/usr/lib/python3.12/unittest/loader.py", line 137, in loadTestsFromName
    module = __import__(module_name)
  File "/tmp/rojo/test_u_imp.py", line 2, in <module>
    from calc import nada
ImportError: cannot import name 'nada' from 'calc' (/tmp/rojo/calc.py)


----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
"""
SALIDA_UNITTEST_SIN_TESTS = """\

----------------------------------------------------------------------
Ran 0 tests in 0.000s

NO TESTS RAN
"""
SALIDA_ATTRIBUTE_ERROR = """\
E
======================================================================
ERROR: test_suma (test_calc.PruebaSumar.test_suma)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "test_calc.py", line 7, in test_suma
    self.assertEqual(calc.sumar(1, 2), 3)
AttributeError: module 'calc' has no attribute 'sumar'

----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
"""


# ---- utilidades ------------------------------------------------------------------------------------------
def borrar(ruta):
    """rmtree que también borra lo de solo lectura (en Windows, los objetos de git lo son)."""
    for raiz, carpetas, archivos in os.walk(str(ruta)):
        for nombre in carpetas + archivos:
            try:
                os.chmod(os.path.join(raiz, nombre), stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
            except OSError:
                pass
    shutil.rmtree(str(ruta), ignore_errors=True)


def escribir(ruta, texto):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(str(ruta), "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    return ruta


def sha256(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def lineas_bajo(salida, titulo):
    """Las líneas «| ...» que siguen a un título de la salida (sin la barra)."""
    lineas = salida.splitlines()
    for i, l in enumerate(lineas):
        if l.strip() == titulo:
            resultado = []
            for siguiente in lineas[i + 1:]:
                if not siguiente.strip().startswith("|"):
                    break
                resultado.append(siguiente.strip()[2:])
            return resultado
    raise AssertionError("no está el título «%s» en la salida:\n%s" % (titulo, salida))


# ---- limpieza (funciones puras) --------------------------------------------------------------------------
class PruebaLimpiar(unittest.TestCase):
    def test_un_parche_limpio_queda_igual(self):
        r = ap.limpiar(PARCHE_A)
        self.assertEqual(r.texto, PARCHE_A)
        self.assertEqual(r.notas, [])

    def test_quita_la_valla_con_diff(self):
        r = ap.limpiar("```diff\n" + PARCHE_A + "```\n")
        self.assertEqual(r.texto, PARCHE_A)
        self.assertTrue(any("2 líneas de vallas" in n for n in r.notas), r.notas)

    def test_quita_la_valla_de_cuatro_acentos(self):
        self.assertEqual(ap.limpiar("````diff\n" + PARCHE_A + "````\n").texto, PARCHE_A)

    def test_quita_la_valla_sin_etiqueta_y_la_de_tildes(self):
        self.assertEqual(ap.limpiar("```\n" + PARCHE_A + "```\n").texto, PARCHE_A)
        self.assertEqual(ap.limpiar("~~~diff\n" + PARCHE_A + "~~~\n").texto, PARCHE_A)

    def test_vallas_con_finales_de_linea_crlf(self):
        texto = ("```diff\n" + PARCHE_A + "```\n").replace("\n", "\r\n")
        r = ap.limpiar(texto)
        self.assertEqual(r.texto, PARCHE_A)

    def test_descarta_la_prosa_que_rodea_al_bloque(self):
        texto = ("Aquí tienes el parche:\n\n```diff\n" + PARCHE_A + "```\n\nPara aplicarlo, corre:\n\n"
                 "```powershell\ngit apply x.patch\n```\n")
        r = ap.limpiar(texto)
        self.assertEqual(r.texto, PARCHE_A)
        self.assertTrue(any("descarté 3 líneas" in n for n in r.notas), r.notas)

    def test_conserva_solo_los_bloques_que_son_diff(self):
        texto = ("```diff\n" + PARCHE_A + "```\n```markdown\n# Reporte\n- hecho\n```\n"
                 "```powershell\ncd x\n```\n")
        self.assertEqual(ap.limpiar(texto).texto, PARCHE_A)

    def test_une_varios_bloques_diff_en_orden(self):
        texto = "```diff\n" + PARCHE_A + "```\n\n```diff\n" + PARCHE_B + "```\n"
        self.assertEqual(ap.limpiar(texto).texto, PARCHE_A + PARCHE_B)

    def test_sirve_si_falta_la_valla_de_apertura_o_la_de_cierre(self):
        self.assertEqual(ap.limpiar("```diff\n" + PARCHE_A).texto, PARCHE_A)
        self.assertEqual(ap.limpiar(PARCHE_A + "```\n").texto, PARCHE_A)

    def test_una_linea_de_contexto_que_parece_valla_no_se_toca(self):
        self.assertEqual(ap.limpiar(PARCHE_MD).texto, PARCHE_MD)
        r = ap.limpiar("````diff\n" + PARCHE_MD + "````\n")
        self.assertEqual(r.texto, PARCHE_MD)
        self.assertTrue(any("2 líneas de vallas" in n for n in r.notas), r.notas)

    def test_descarta_prosa_sin_vallas_antes_y_despues(self):
        sin_separador = ap.limpiar("Aquí está el parche:\n" + PARCHE_A + "Para aplicarlo corre algo.\n")
        self.assertEqual(sin_separador.texto, PARCHE_A)
        # se deja a lo más una línea vacía: puede ser un contexto en blanco al que el editor le quitó el espacio
        con_separador = ap.limpiar("Aquí está el parche:\n" + PARCHE_A + "\nPara aplicarlo corre algo.\n")
        self.assertEqual(con_separador.texto, PARCHE_A + "\n")

    def test_conserva_una_linea_vacia_final_que_es_contexto(self):
        texto = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1,3 +1,3 @@\n uno\n-dos\n+DOS\n\n"
        self.assertEqual(ap.limpiar(texto).texto, texto)

    def test_sin_parche_es_un_error(self):
        for texto in ("", "   \n\n", "hola\nesto no es un parche\n", "```\nnada\n```\n", "```diff\n```\n"):
            with self.subTest(texto=texto):
                with self.assertRaises(ap.ErrorParche):
                    ap.limpiar(texto)

    def test_crlf_en_todo_el_parche_pasa_a_lf(self):
        r = ap.limpiar(PARCHE_A.replace("\n", "\r\n"))
        self.assertEqual(r.texto, PARCHE_A)
        self.assertTrue(any("CRLF" in n for n in r.notas), r.notas)

    def test_crlf_solo_en_el_contenido_es_legitimo_y_se_conserva(self):
        # lo que produce «git diff» sobre un archivo CRLF: encabezados con LF y contenido con CRLF
        texto = ("diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1,2 +1,2 @@\n"
                 " uno\r\n-dos\r\n+DOS\r\n")
        r = ap.limpiar(texto)
        self.assertEqual(r.texto, texto)
        self.assertEqual(r.notas, [])

    def test_agrega_el_salto_de_linea_final(self):
        r = ap.limpiar(PARCHE_A.rstrip("\n"))
        self.assertEqual(r.texto, PARCHE_A)
        self.assertTrue(any("salto de línea final" in n for n in r.notas), r.notas)

    def test_no_corta_las_lineas_en_caracteres_raros(self):
        # str.splitlines() cortaría en \x0c, \x85 y \u2028, que pueden estar dentro del código
        texto = ("diff --git a/r.txt b/r.txt\nnew file mode 100644\n--- /dev/null\n+++ b/r.txt\n"
                 "@@ -0,0 +1,2 @@\n+a\x0cb\u2028c\x85d\n+fin\n")
        self.assertEqual(ap.limpiar(texto).texto, texto)

    def test_acepta_un_parche_sin_la_linea_diff_git(self):
        texto = "--- a/a.txt\n+++ b/a.txt\n@@ -1,2 +1,2 @@\n uno\n-dos\n+DOS\n"
        self.assertEqual(ap.limpiar(texto).texto, texto)

    def test_no_recorta_los_datos_de_un_parche_binario(self):
        texto = ("diff --git a/x.bin b/x.bin\nnew file mode 100644\nindex 0000000..1234567\n"
                 "GIT binary patch\nliteral 4\nLcmZQzU|?uq0RR91\n\nliteral 0\nHcmV?d00001\n\n")
        self.assertEqual(ap.limpiar(texto).texto, texto)

    def test_es_idempotente(self):
        entradas = ["```diff\n" + PARCHE_A + "```\n", PARCHE_A.replace("\n", "\r\n"), PARCHE_A.rstrip("\n"),
                    "Hola:\n" + PARCHE_A + "\nChao\n", "````diff\n" + PARCHE_MD + "````\n"]
        for texto in entradas:
            with self.subTest(texto=texto):
                una_vez = ap.limpiar(texto).texto
                self.assertEqual(ap.limpiar(una_vez).texto, una_vez)


class PruebaDecodificar(unittest.TestCase):
    def test_utf8_plano(self):
        texto, notas = ap.decodificar("ñandú\n".encode("utf-8"))
        self.assertEqual((texto, notas), ("ñandú\n", []))

    def test_utf8_con_bom(self):
        texto, notas = ap.decodificar(b"\xef\xbb\xbf" + "ñ\n".encode("utf-8"))
        self.assertEqual(texto, "ñ\n")
        self.assertTrue(any("BOM" in n for n in notas), notas)

    def test_utf16_con_bom_en_los_dos_ordenes(self):
        for datos in (b"\xff\xfe" + "ñ\n".encode("utf-16-le"), b"\xfe\xff" + "ñ\n".encode("utf-16-be")):
            with self.subTest(datos=datos):
                texto, notas = ap.decodificar(datos)
                self.assertEqual(texto, "ñ\n")
                self.assertTrue(any("UTF-16" in n for n in notas), notas)

    def test_lo_que_no_es_utf8_es_un_error_con_instrucciones(self):
        with self.assertRaises(ap.ErrorParche) as ctx:
            ap.decodificar("ñ\n".encode("cp1252"))
        self.assertIn("UTF-8", str(ctx.exception))

    def test_bytes_nulos_sin_bom_es_un_error(self):
        with self.assertRaises(ap.ErrorParche):
            ap.decodificar(b"abc\x00def")


# ---- elegir el parche (sin git) ----------------------------------------------------------------------------
class PruebaCarpetaDeParches(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="test-aplicar-"))
        self.addCleanup(borrar, self.base)
        self.home = self.base / "home"
        self.home.mkdir()

    def config(self, contenido, bom=False):
        datos = json.dumps(contenido).encode("utf-8")
        (self.home / ".metodo-ia.json").write_bytes((b"\xef\xbb\xbf" if bom else b"") + datos)

    def parche(self, carpeta, nombre, antiguedad_s=0):
        ruta = escribir(Path(carpeta) / nombre, "x\n")
        t = time.time() - antiguedad_s
        os.utime(str(ruta), (t, t))
        return ruta

    def test_usa_la_carpeta_del_json(self):
        carpeta = self.base / "mis parches"
        carpeta.mkdir()
        self.config({"carpeta_parches": str(carpeta)})
        self.assertEqual(ap.leer_carpeta_parches(self.home), (carpeta, []))

    def test_el_json_puede_traer_bom(self):
        carpeta = self.base / "p"
        carpeta.mkdir()
        self.config({"carpeta_parches": str(carpeta)}, bom=True)
        self.assertEqual(ap.leer_carpeta_parches(self.home)[0], carpeta)

    def test_expande_la_tilde_y_las_variables_de_entorno(self):
        (self.home / "misparches").mkdir()
        self.config({"carpeta_parches": "~/misparches"})
        self.assertEqual(ap.leer_carpeta_parches(self.home)[0], self.home / "misparches")
        otra = self.base / "otra"
        otra.mkdir()
        self.config({"carpeta_parches": "$CARPETA_DE_PRUEBA_APLICAR"})
        with mock.patch.dict(os.environ, {"CARPETA_DE_PRUEBA_APLICAR": str(otra)}):
            self.assertEqual(ap.leer_carpeta_parches(self.home)[0], otra)

    def test_sin_json_o_sin_la_clave_usa_downloads(self):
        (self.home / "Downloads").mkdir()
        self.assertEqual(ap.leer_carpeta_parches(self.home), (self.home / "Downloads", []))
        self.config({"otra_cosa": 1})
        self.assertEqual(ap.leer_carpeta_parches(self.home)[0], self.home / "Downloads")

    def test_usa_descargas_si_no_hay_downloads_y_downloads_gana_si_hay_las_dos(self):
        (self.home / "Descargas").mkdir()
        self.assertEqual(ap.leer_carpeta_parches(self.home)[0], self.home / "Descargas")
        (self.home / "Downloads").mkdir()
        self.assertEqual(ap.leer_carpeta_parches(self.home)[0], self.home / "Downloads")

    def test_una_carpeta_configurada_que_no_existe_es_un_error(self):
        (self.home / "Downloads").mkdir()  # no se cae en silencio a otra carpeta: podría tomar otro parche
        self.config({"carpeta_parches": str(self.base / "no-existe")})
        with self.assertRaises(ap.ErrorUso):
            ap.leer_carpeta_parches(self.home)

    def test_un_json_roto_avisa_y_usa_la_carpeta_por_defecto(self):
        (self.home / "Downloads").mkdir()
        (self.home / ".metodo-ia.json").write_bytes(b"{esto no es json")
        carpeta, avisos = ap.leer_carpeta_parches(self.home)
        self.assertEqual(carpeta, self.home / "Downloads")
        self.assertEqual(len(avisos), 1)

    def test_sin_ninguna_carpeta_es_un_error_que_explica_que_hacer(self):
        with self.assertRaises(ap.ErrorUso) as ctx:
            ap.leer_carpeta_parches(self.home)
        self.assertIn("carpeta_parches", str(ctx.exception))

    def test_el_parche_mas_reciente_gana_por_fecha(self):
        self.parche(self.base, "viejo.patch", 7200)
        self.parche(self.base, "nuevo.patch", 10)
        self.parche(self.base, "medio.patch", 3600)
        self.assertEqual(ap.parche_mas_reciente(self.base)[0].name, "nuevo.patch")

    def test_ignora_lo_que_no_es_un_patch_y_acepta_mayusculas(self):
        self.parche(self.base, "notas.txt", 1)
        self.parche(self.base, "otro.diff", 1)
        self.parche(self.base, "T-001.PATCH", 100)
        (self.base / "carpeta.patch").mkdir()
        self.assertEqual(ap.parche_mas_reciente(self.base)[0].name, "T-001.PATCH")

    def test_carpeta_sin_parches(self):
        self.assertEqual(ap.parche_mas_reciente(self.base), (None, []))

    def test_avisa_si_hay_un_patch_txt_mas_nuevo(self):
        self.parche(self.base, "T-001.patch", 600)
        self.parche(self.base, "T-002.patch.txt", 5)
        elegido, avisos = ap.parche_mas_reciente(self.base)
        self.assertEqual(elegido.name, "T-001.patch")
        self.assertEqual(len(avisos), 1)
        self.assertIn("T-002.patch.txt", avisos[0])

    def test_un_patch_txt_mas_viejo_no_avisa(self):
        self.parche(self.base, "T-001.patch.txt", 600)
        self.parche(self.base, "T-002.patch", 5)
        self.assertEqual(ap.parche_mas_reciente(self.base)[1], [])

    def test_resolver_con_la_ruta_completa(self):
        ruta = self.parche(self.base, "T-001.patch")
        self.assertEqual(ap.resolver_parche(str(ruta), self.home), (ruta, []))

    def test_resolver_sin_argumento_toma_el_mas_reciente_de_la_carpeta_de_parches(self):
        descargas = self.home / "Downloads"
        descargas.mkdir()
        self.parche(descargas, "viejo.patch", 900)
        nuevo = self.parche(descargas, "nuevo.patch", 5)
        self.assertEqual(ap.resolver_parche(None, self.home)[0], nuevo)

    def test_un_nombre_suelto_se_busca_tambien_en_la_carpeta_de_parches(self):
        descargas = self.home / "Downloads"
        descargas.mkdir()
        ruta = self.parche(descargas, "T-007.patch")
        self.assertEqual(ap.resolver_parche("T-007.patch", self.home)[0], ruta)

    def test_el_archivo_del_directorio_actual_gana_sobre_la_carpeta_de_parches(self):
        descargas = self.home / "Downloads"
        descargas.mkdir()
        self.parche(descargas, "T-007.patch")
        aqui = self.base / "aqui"
        aqui.mkdir()
        propio = self.parche(aqui, "T-007.patch")
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(str(aqui))
        self.assertEqual(Path(ap.resolver_parche("T-007.patch", self.home)[0]).resolve(), propio.resolve())

    def test_un_parche_que_no_existe_o_una_carpeta_es_un_error(self):
        with self.assertRaises(ap.ErrorUso):
            ap.resolver_parche(str(self.base / "no-existe.patch"), self.home)
        with self.assertRaises(ap.ErrorUso):
            ap.resolver_parche(str(self.base), self.home)

    def test_carpeta_vacia_dice_que_no_hay_parches(self):
        (self.home / "Downloads").mkdir()
        with self.assertRaises(ap.ErrorUso) as ctx:
            ap.resolver_parche(None, self.home)
        self.assertIn("no hay ningún archivo .patch", str(ctx.exception))


# ---- base para las pruebas que usan git ---------------------------------------------------------------------
@unittest.skipUnless(HAY_GIT, "git no está instalado")
class PruebaConGit(unittest.TestCase):
    """Un repo temporal, un HOME aislado con su Downloads y un git sin la configuración de quien corre las pruebas."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="test-aplicar-"))
        self.addCleanup(borrar, self.base)
        self.home = self.base / "home"
        self.descargas = self.home / "Downloads"
        self.descargas.mkdir(parents=True)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        vacio = escribir(self.base / "gitconfig-vacio", "")
        entorno = {"HOME": str(self.home), "USERPROFILE": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config"),
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(vacio), "GIT_TERMINAL_PROMPT": "0"}
        parche_entorno = mock.patch.dict(os.environ, entorno)
        parche_entorno.start()
        self.addCleanup(parche_entorno.stop)
        self.git("init", "-q", ".")
        self.git("config", "user.email", "prueba@example.com")
        self.git("config", "user.name", "Prueba")
        self.git("config", "core.autocrlf", "false")

    def git(self, *args, **kw):
        r = subprocess.run(["git"] + list(args), cwd=str(kw.get("cwd", self.repo)), capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            self.fail("git %s falló: %s" % (" ".join(args), r.stderr))
        return r.stdout

    def git_bytes(self, *args):
        r = subprocess.run(["git"] + list(args), cwd=str(self.repo), capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def escribir(self, rel, texto):
        return escribir(self.repo / rel, texto)

    def leer(self, rel):
        return (self.repo / rel).read_bytes()

    def confirmar(self):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")

    def estado(self):
        return self.git("status", "--porcelain")

    def parche(self, nombre, texto, antiguedad_s=0):
        return self.parche_bytes(nombre, texto.encode("utf-8"), antiguedad_s)

    def parche_bytes(self, nombre, datos, antiguedad_s=0):
        ruta = self.descargas / nombre
        ruta.write_bytes(datos)
        t = time.time() - antiguedad_s
        os.utime(str(ruta), (t, t))
        return ruta

    def correr(self, parche=None, estricto=None, solo_check=False, cwd=None):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = ap.ejecutar(str(parche) if parche is not None else None, estricto, solo_check,
                                 cwd=cwd or self.repo, home=self.home)
        return codigo, salida.getvalue()

    def correr_cli(self, *args, **kw):
        entorno = dict(os.environ, **kw.get("entorno", {}))
        return subprocess.run([sys.executable, str(FUENTE)] + list(args), cwd=str(kw.get("cwd", self.repo)),
                              capture_output=True, env=entorno)


# ---- la cadena de seguridad -------------------------------------------------------------------------------------
class PruebaCadena(PruebaConGit):
    def setUp(self):
        super().setUp()
        self.escribir("a.txt", ARCHIVO_A)
        self.confirmar()

    def test_aplica_con_el_check_simple_y_no_guarda_nada(self):
        self.parche("T-001-a.patch", PARCHE_A)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(self.leer("a.txt"), ARCHIVO_A_DESPUES.encode("utf-8"))
        self.assertIn("pasó el «git apply --check» simple", salida)
        self.assertEqual(self.estado(), " M a.txt\n")  # modificado, sin pasar por el índice
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "")

    def test_sin_argumento_aplica_el_parche_mas_reciente(self):
        self.parche("T-000-viejo.patch", PARCHE_B, antiguedad_s=7200)
        self.parche("T-001-a.patch", PARCHE_A, antiguedad_s=5)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(self.leer("a.txt"), ARCHIVO_A_DESPUES.encode("utf-8"))

    def test_aplica_un_parche_guardado_con_vallas_de_markdown(self):
        self.parche("T-001-a.patch", "```diff\n" + PARCHE_A + "```\n")
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(self.leer("a.txt"), ARCHIVO_A_DESPUES.encode("utf-8"))
        self.assertIn("Limpieza: quité 2 líneas de vallas", salida)

    def test_conteos_de_bloque_equivocados_se_arreglan_con_recount(self):
        self.parche("T-001-a.patch", PARCHE_A.replace("@@ -1,5 +1,5 @@", "@@ -1,9 +1,9 @@"))
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("pasó con «--recount»", salida)
        self.assertEqual(self.leer("a.txt"), ARCHIVO_A_DESPUES.encode("utf-8"))

    def test_tabuladores_contra_espacios_se_arreglan_con_ignore_whitespace(self):
        self.escribir("t.txt", "uno\n\tdos\ntres\ncuatro\n")
        self.confirmar()
        parche = ("diff --git a/t.txt b/t.txt\n--- a/t.txt\n+++ b/t.txt\n@@ -1,4 +1,4 @@\n"
                  " uno\n     dos\n-tres\n+TRES\n cuatro\n")
        self.parche("T-001-t.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("pasó con «--recount --ignore-whitespace»", salida)
        self.assertEqual(self.leer("t.txt"), b"uno\n\tdos\nTRES\ncuatro\n")
        self.assertIn("--ignore-whitespace", salida.split("Avisos")[1])

    def test_la_cadena_es_acumulativa(self):
        # conteos equivocados Y tabuladores a la vez: el tercer paso necesita las dos banderas juntas
        self.escribir("t.txt", "uno\n\tdos\ntres\ncuatro\n")
        self.confirmar()
        parche = ("diff --git a/t.txt b/t.txt\n--- a/t.txt\n+++ b/t.txt\n@@ -1,9 +1,9 @@\n"
                  " uno\n     dos\n-tres\n+TRES\n cuatro\n")
        self.parche("T-001-t.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("pasó con «--recount --ignore-whitespace»", salida)
        self.assertEqual(self.leer("t.txt"), b"uno\n\tdos\nTRES\ncuatro\n")

    def test_archivo_con_crlf_y_parche_lf_se_arregla_con_ignore_whitespace(self):
        (self.repo / "w.txt").write_bytes(b"uno\r\ndos\r\ntres\r\ncuatro\r\n")
        self.confirmar()
        parche = ("diff --git a/w.txt b/w.txt\n--- a/w.txt\n+++ b/w.txt\n@@ -1,4 +1,4 @@\n"
                  " uno\n dos\n-tres\n+TRES\n cuatro\n")
        self.parche("T-001-w.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("pasó con «--recount --ignore-whitespace»", salida)
        self.assertIn(b"TRES", self.leer("w.txt"))

    def test_un_parche_con_crlf_en_todo_no_deja_un_cr_pegado_en_el_archivo(self):
        # con «--ignore-whitespace» git lo aceptaría, pero dejaría «CUATRO\r\n» dentro de un archivo LF
        self.parche_bytes("T-001-a.patch", PARCHE_A.replace("\n", "\r\n").encode("utf-8"))
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(self.leer("a.txt"), ARCHIVO_A_DESPUES.encode("utf-8"))
        self.assertIn("convertí los finales de línea de CRLF a LF", salida)
        self.assertIn("pasó el «git apply --check» simple", salida)

    def test_replica_de_windows_archivos_crlf_en_disco_y_autocrlf_true(self):
        # como en el equipo de la persona: el archivo está en CRLF en disco y git lo guarda con LF
        self.git("config", "core.autocrlf", "true")
        (self.repo / "win.txt").write_bytes(b"uno\r\ndos\r\ntres\r\ncuatro\r\ncinco\r\n")
        self.confirmar()
        self.assertEqual(self.git("show", "HEAD:win.txt"), ARCHIVO_A)
        self.parche("T-001-win.patch", PARCHE_A.replace("a.txt", "win.txt"))  # el parche del LLM viene con LF
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(self.leer("win.txt"), b"uno\r\ndos\r\ntres\r\nCUATRO\r\ncinco\r\n")
        self.assertIn("pasó el «git apply --check» simple", salida)

    def test_un_git_diff_sobre_un_archivo_crlf_se_respeta(self):
        (self.repo / "w.txt").write_bytes(b"uno\r\ndos\r\ntres\r\n")
        self.confirmar()
        (self.repo / "w.txt").write_bytes(b"uno\r\nDOS\r\ntres\r\n")
        parche = self.git_bytes("diff")
        self.git("checkout", "--", "w.txt")
        self.assertIn(b"\r\n-dos\r\n", parche)  # el contenido trae CR y los encabezados no
        self.parche_bytes("T-001-w.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(self.leer("w.txt"), b"uno\r\nDOS\r\ntres\r\n")
        self.assertNotIn("convertí", salida)

    def test_crea_borra_y_renombra_archivos(self):
        self.escribir("viejo.txt", "uno\ndos\ntres\ncuatro\n")
        self.escribir("borrar.txt", "x\n")
        self.confirmar()
        parche = ("diff --git a/viejo.txt b/nuevo.txt\nsimilarity index 75%\nrename from viejo.txt\nrename to nuevo.txt\n"
                  "--- a/viejo.txt\n+++ b/nuevo.txt\n@@ -1,4 +1,4 @@\n uno\n-dos\n+DOS\n tres\n cuatro\n"
                  "diff --git a/borrar.txt b/borrar.txt\ndeleted file mode 100644\n--- a/borrar.txt\n+++ /dev/null\n"
                  "@@ -1 +0,0 @@\n-x\n") + parche_archivo_nuevo("creado.txt", "hola\n")
        self.parche("T-001-varios.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertFalse((self.repo / "viejo.txt").exists())
        self.assertFalse((self.repo / "borrar.txt").exists())
        self.assertEqual(self.leer("nuevo.txt"), b"uno\nDOS\ntres\ncuatro\n")
        self.assertEqual(self.leer("creado.txt"), b"hola\n")
        self.assertIn("Aplicado (3 archivos)", salida)
        self.assertIn("(antes: viejo.txt)", salida)

    def test_nombres_de_archivo_con_espacios_y_tildes(self):
        self.escribir("a b.txt", "uno\ndos\n")
        self.escribir("ñandú.txt", "x\ny\n")
        self.confirmar()
        parche = ("diff --git a/a b.txt b/a b.txt\n--- a/a b.txt\n+++ b/a b.txt\n@@ -1,2 +1,2 @@\n uno\n-dos\n+DOS\n"
                  "diff --git a/ñandú.txt b/ñandú.txt\n--- a/ñandú.txt\n+++ b/ñandú.txt\n@@ -1,2 +1,2 @@\n x\n-y\n+Y\n")
        self.parche("T-001-nombres.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(self.leer("a b.txt"), b"uno\nDOS\n")
        self.assertEqual(self.leer("ñandú.txt"), b"x\nY\n")

    def test_desde_una_subcarpeta_aplica_de_verdad(self):
        # sin la raíz del repo, «git apply» devuelve 0 pero no aplica nada de lo que está fuera de la subcarpeta
        self.escribir("sub/otro.txt", "x\n")
        self.confirmar()
        self.parche("T-001-a.patch", PARCHE_A)
        codigo, salida = self.correr(cwd=self.repo / "sub")
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(self.leer("a.txt"), ARCHIVO_A_DESPUES.encode("utf-8"))

    def test_check_no_aplica_nada(self):
        ruta = self.parche("T-001-a.patch", PARCHE_A)
        codigo, salida = self.correr(solo_check=True)
        self.assertEqual(codigo, 0, salida)
        self.assertIn("Ensayo (--check)", salida)
        self.assertEqual(self.leer("a.txt"), ARCHIVO_A.encode("utf-8"))
        self.assertEqual(self.estado(), "")
        self.assertTrue(ruta.exists())

    def test_check_con_un_parche_que_no_encaja_diagnostica_y_da_1(self):
        self.escribir("a.txt", ARCHIVO_A.replace("cuatro", "cuatro-DISTINTO"))
        self.confirmar()
        self.parche("T-001-a.patch", PARCHE_A)
        codigo, salida = self.correr(solo_check=True)
        self.assertEqual(codigo, 1, salida)
        self.assertIn("El parche esperaba:", salida)

    def test_un_nombre_suelto_se_busca_en_la_carpeta_de_parches(self):
        self.parche("T-001-a.patch", PARCHE_A)
        codigo, salida = self.correr(parche="T-001-a.patch")
        self.assertEqual(codigo, 0, salida)

    def test_avisa_si_el_parche_tiene_mas_de_una_hora(self):
        self.parche("T-001-a.patch", PARCHE_A, antiguedad_s=3 * 3600)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("más de 1 hora", salida)

    def test_un_parche_reciente_no_avisa_de_antiguedad(self):
        self.parche("T-001-a.patch", PARCHE_A)
        self.assertNotIn("más de 1 hora", self.correr()[1])

    def test_avisa_de_un_patch_txt_mas_nuevo(self):
        self.parche("T-001-a.patch", PARCHE_A, antiguedad_s=60)
        self.parche("T-002-b.patch.txt", PARCHE_B, antiguedad_s=1)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("T-002-b.patch.txt", salida)

    def test_avisa_si_el_repo_ya_tiene_cambios_sin_guardar(self):
        self.escribir("suelto.txt", "x\n")
        self.parche("T-001-a.patch", PARCHE_A)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 0, salida)
        self.assertIn("1 archivo con cambios sin guardar", salida)

    def test_un_repo_limpio_no_avisa_de_cambios(self):
        self.parche("T-001-a.patch", PARCHE_A)
        self.assertNotIn("cambios sin guardar", self.correr()[1])

    def test_el_propio_parche_dentro_del_repo_no_cuenta_como_cambio(self):
        ruta = escribir(self.repo / "T-001-a.patch", PARCHE_A)
        codigo, salida = self.correr(parche=ruta)
        self.assertEqual(codigo, 0, salida)
        self.assertNotIn("cambios sin guardar", salida)

    def test_un_parche_con_tildes_en_el_nombre_dentro_del_repo_no_cuenta_como_cambio(self):
        # «git status --short» escribe «parche-\303\261and\303\272.patch» salvo con core.quotepath=off
        ruta = escribir(self.repo / "parche-ñandú.patch", PARCHE_A)
        codigo, salida = self.correr(parche=ruta)
        self.assertEqual(codigo, 0, salida)
        self.assertNotIn("cambios sin guardar", salida)

    def test_no_toca_el_archivo_del_parche(self):
        ruta = self.parche("T-001-a.patch", "```diff\n" + PARCHE_A + "```\n")
        antes = sha256(ruta)
        self.correr()
        self.assertEqual(sha256(ruta), antes)
        self.assertEqual(sorted(p.name for p in self.descargas.iterdir()), ["T-001-a.patch"])

    def test_no_deja_archivos_temporales_ni_si_sale_bien_ni_si_sale_mal(self):
        temporal = self.base / "tmp"
        temporal.mkdir()
        with mock.patch.object(tempfile, "tempdir", str(temporal)):
            self.parche("T-001-a.patch", PARCHE_A)
            self.assertEqual(self.correr()[0], 0)
            self.assertEqual(os.listdir(str(temporal)), [])
            self.parche("T-002-malo.patch", PARCHE_A.replace("cuatro", "otra-cosa"))
            self.assertEqual(self.correr()[0], 1)
            self.assertEqual(os.listdir(str(temporal)), [])

    def test_sin_parches_en_la_carpeta_da_2(self):
        codigo, salida = self.correr()
        self.assertEqual(codigo, 2)
        self.assertIn("no hay ningún archivo .patch", salida)

    def test_un_archivo_que_no_es_un_parche_da_1(self):
        self.parche("T-001-a.patch", "Hola, esto es solo texto.\n")
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1)
        self.assertIn("No pude usar el parche", salida)


# ---- el diagnóstico -------------------------------------------------------------------------------------------
class PruebaDiagnosticoCorrupto(unittest.TestCase):
    """El diagnóstico conserva contexto con las salidas de distintas versiones de git."""

    def comprobar_contexto(self, mensaje):
        reverso = subprocess.CompletedProcess([], 1, stdout="", stderr=mensaje)
        with mock.patch.object(ap, "_git", return_value=reverso) as git, \
                mock.patch.object(ap, "archivos_del_parche", side_effect=AssertionError(
                    "un parche corrupto reconocido no necesita diagnosticar rechazos")):
            lineas, pedir_correccion = ap.diagnosticar(
                Path("."), PARCHE_ROTO, "roto.patch", [("simple", 1, mensaje)])
        salida = "\n".join(lineas)
        self.assertTrue(pedir_correccion)
        self.assertIn("dañado cerca de la línea 4", salida)
        self.assertRegex(salida, r">\s+4 \| @@ -1,3 \+1,3(?:\n|$)")
        self.assertIn("   3 | +++ b/a.txt", salida)
        self.assertIn("   5 |  uno", salida)
        git.assert_called_once()  # solo el ensayo de reverso; no aplicar ni crear copias

    def test_formato_con_linea_sin_ruta(self):
        self.comprobar_contexto("error: corrupt patch at line 4\n")

    def test_formato_con_ruta_temporal_del_ci(self):
        self.comprobar_contexto("error: corrupt patch at /tmp/aplicar-jr8oex4s.patch:4\n")

    def test_formato_con_ruta_windows_espacios_y_dos_puntos(self):
        self.comprobar_contexto("aviso previo\r\nerror: corrupt patch at "
                               r"C:\Temp\carpeta con espacios\parche:12.patch:4" + "\r\n")


class PruebaDiagnostico(PruebaConGit):
    LARGO = "".join("linea %d\n" % i for i in range(1, 13))
    PARCHE_LARGO = ("diff --git a/largo.txt b/largo.txt\n--- a/largo.txt\n+++ b/largo.txt\n@@ -4,7 +4,7 @@\n"
                    " linea 4\n linea 5\n linea 6\n-linea 7\n+LINEA 7\n linea 8\n linea 9\n linea 10\n")

    def instantanea(self):
        archivos = {}
        for ruta in sorted(self.repo.rglob("*")):
            if ".git" in ruta.parts or not ruta.is_file():
                continue
            archivos[ruta.relative_to(self.repo).as_posix()] = sha256(ruta)
        return archivos, self.estado()

    def test_muestra_las_3_lineas_que_esperaba_el_parche_y_las_3_que_tiene_el_archivo(self):
        self.escribir("largo.txt", self.LARGO.replace("linea 7", "linea 7 (editada)"))
        self.confirmar()
        self.parche("T-001-largo.patch", self.PARCHE_LARGO)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("largo.txt: 1 bloque no encaja", salida)
        self.assertIn("@@ -4,7 +4,7 @@  (desde la línea 7 del archivo)", salida)
        self.assertEqual(lineas_bajo(salida, "El parche esperaba:"), ["linea 7", "linea 8", "linea 9"])
        self.assertEqual(lineas_bajo(salida, "El archivo tiene:"), ["linea 7 (editada)", "linea 8", "linea 9"])
        self.assertIn("Tu repo no cambió.", salida)
        self.assertIn("Devuélveme solo la parte corregida", salida)
        self.assertNotIn("El resto del parche sí encaja", salida)  # no había más bloques que pudieran encajar

    def test_el_repo_queda_exactamente_igual_tras_diagnosticar(self):
        self.escribir("largo.txt", self.LARGO.replace("linea 7", "linea 7 (editada)"))
        self.confirmar()
        self.escribir("suelto.txt", "sin guardar\n")
        antes = self.instantanea()
        temporal = self.base / "tmp"
        temporal.mkdir()
        self.parche("T-001-largo.patch", self.PARCHE_LARGO)
        with mock.patch.object(tempfile, "tempdir", str(temporal)):
            codigo, _ = self.correr()
        self.assertEqual(codigo, 1)
        self.assertEqual(self.instantanea(), antes)
        self.assertEqual(list(self.repo.rglob("*.rej")), [])
        self.assertEqual(os.listdir(str(temporal)), [])  # tampoco quedan copias temporales

    def test_solo_se_reportan_los_bloques_que_no_encajan(self):
        archivo = "".join("l%d\n" % i for i in range(1, 31))
        self.escribir("dos.txt", archivo.replace("l25\n", "l25 cambiada\n"))
        self.confirmar()
        parche = ("diff --git a/dos.txt b/dos.txt\n--- a/dos.txt\n+++ b/dos.txt\n"
                  "@@ -2,5 +2,5 @@\n l2\n l3\n-l4\n+L4\n l5\n l6\n"
                  "@@ -23,5 +23,5 @@\n l23\n l24\n-l25\n+L25\n l26\n l27\n")
        self.parche("T-001-dos.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("dos.txt: 1 bloque no encaja", salida)
        self.assertIn("@@ -23,5 +23,5 @@", salida)
        self.assertNotIn("@@ -2,5 +2,5 @@", salida)
        self.assertIn("El resto del parche sí encaja", salida)

    def test_si_falla_un_archivo_y_otro_encaja_se_dice(self):
        self.escribir("a.txt", ARCHIVO_A)
        self.escribir("b.txt", "x\ny\n")
        self.escribir("largo.txt", self.LARGO.replace("linea 7", "linea 7 (editada)"))
        self.confirmar()
        self.parche("T-001-dos-archivos.patch", PARCHE_A + PARCHE_B.replace("-y", "-OTRA").replace("+Y", "+Z")
                    + self.PARCHE_LARGO)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("b.txt: 1 bloque no encaja", salida)
        self.assertIn("largo.txt: 1 bloque no encaja", salida)
        self.assertNotIn("a.txt: 1 bloque", salida)
        self.assertIn("El resto del parche sí encaja", salida)

    def test_dos_bloques_que_no_encajan(self):
        archivo = "".join("l%d\n" % i for i in range(1, 31))
        self.escribir("dos.txt", archivo.replace("l4\n", "l4 x\n").replace("l25\n", "l25 y\n"))
        self.confirmar()
        parche = ("diff --git a/dos.txt b/dos.txt\n--- a/dos.txt\n+++ b/dos.txt\n"
                  "@@ -2,5 +2,5 @@\n l2\n l3\n-l4\n+L4\n l5\n l6\n"
                  "@@ -23,5 +23,5 @@\n l23\n l24\n-l25\n+L25\n l26\n l27\n")
        self.parche("T-001-dos.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("dos.txt: 2 bloques no encajan", salida)
        self.assertEqual(salida.count("El parche esperaba:"), 2)

    def test_un_archivo_que_no_existe(self):
        parche = "diff --git a/falta.py b/falta.py\n--- a/falta.py\n+++ b/falta.py\n@@ -1,1 +1,1 @@\n-x\n+y\n"
        self.escribir("a.txt", ARCHIVO_A)
        self.confirmar()
        self.parche("T-001-falta.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("«falta.py», que no existe en tu repo", salida)

    def test_el_nombre_de_un_archivo_con_tildes_que_no_existe_se_muestra_legible(self):
        # los nombres con tildes pasan por la lectura de los mensajes de git sin romperse
        parche = ("diff --git a/ñandú-falta.py b/ñandú-falta.py\n--- a/ñandú-falta.py\n+++ b/ñandú-falta.py\n"
                  "@@ -1,1 +1,1 @@\n-x\n+y\n")
        self.escribir("a.txt", ARCHIVO_A)
        self.confirmar()
        self.parche("T-001-falta.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("«ñandú-falta.py», que no existe en tu repo", salida)

    def test_un_archivo_nuevo_que_ya_existe(self):
        self.escribir("existe.txt", "ya estaba\n")
        self.confirmar()
        self.parche("T-001-existe.patch", parche_archivo_nuevo("existe.txt", "otra cosa\n"))
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("crea «existe.txt», pero ya existe", salida)

    def test_un_parche_ya_aplicado_se_dice_y_no_manda_a_pedir_correcciones(self):
        self.escribir("a.txt", ARCHIVO_A)
        self.confirmar()
        self.parche("T-001-a.patch", PARCHE_A)
        self.assertEqual(self.correr()[0], 0)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("ya está aplicado", salida)
        self.assertNotIn("Devuélveme solo la parte corregida", salida)
        self.assertEqual(self.leer("a.txt"), ARCHIVO_A_DESPUES.encode("utf-8"))

    def test_un_parche_danado_muestra_las_lineas_que_rodean_el_error(self):
        self.escribir("a.txt", "uno\ndos\ntres\n")
        self.confirmar()
        self.parche("T-001-roto.patch", PARCHE_ROTO)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("dañado cerca de la línea 4", salida)
        self.assertRegex(salida, r">\s+4 \| @@ -1,3 \+1,3\n")  # la marca > señala la línea que dice git
        self.assertIn("   3 | +++ b/a.txt", salida)
        self.assertIn("   5 |  uno", salida)

    def test_si_solo_difieren_los_espacios_se_muestran_con_repr(self):
        # git no perdona un espacio sobrante al final de línea, ni siquiera con --ignore-whitespace
        self.escribir("a.txt", "uno\ndos \ntres\ncuatro\ncinco\n")
        self.confirmar()
        self.parche("T-001-a.patch", PARCHE_A)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("Las líneas se ven iguales", salida)
        self.assertEqual(lineas_bajo(salida, "El parche esperaba:"), ["'uno'", "'dos'", "'tres'"])
        self.assertEqual(lineas_bajo(salida, "El archivo tiene:"), ["'uno'", "'dos '", "'tres'"])

    def test_funciona_aunque_la_carpeta_temporal_este_dentro_de_otro_repo(self):
        # dentro de un repo, «git apply --reject» dice «Skipped patch» y sale 0 sin dejar ningún .rej
        self.escribir("largo.txt", self.LARGO.replace("linea 7", "linea 7 (editada)"))
        self.confirmar()
        otro = self.base / "otro"
        otro.mkdir()
        self.git("init", "-q", ".", cwd=otro)
        temporal = otro / "tmp"
        temporal.mkdir()
        self.parche("T-001-largo.patch", self.PARCHE_LARGO)
        with mock.patch.object(tempfile, "tempdir", str(temporal)):
            codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertEqual(lineas_bajo(salida, "El archivo tiene:")[0], "linea 7 (editada)")

    def test_archivos_con_espacios_y_tildes_tambien_se_diagnostican(self):
        self.escribir("carpeta uno/ñandú y co.txt", self.LARGO.replace("linea 7", "linea 7 (editada)"))
        self.confirmar()
        parche = self.PARCHE_LARGO.replace("largo.txt", "carpeta uno/ñandú y co.txt")
        self.parche("T-001-nombres.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("carpeta uno/ñandú y co.txt: 1 bloque no encaja", salida)
        self.assertEqual(lineas_bajo(salida, "El archivo tiene:")[0], "linea 7 (editada)")

    def test_el_diagnostico_usa_la_misma_tolerancia_que_la_cadena(self):
        archivo = "".join("l%d\n" % i for i in range(1, 31))
        self.escribir("dos.txt", archivo.replace("l3\n", "\tl3\n").replace("l25\n", "l25 cambiada\n"))
        self.confirmar()
        parche = ("diff --git a/dos.txt b/dos.txt\n--- a/dos.txt\n+++ b/dos.txt\n"
                  "@@ -2,5 +2,5 @@\n l2\n     l3\n-l4\n+L4\n l5\n l6\n"  # solo difiere en tabuladores: encaja
                  "@@ -23,5 +23,5 @@\n l23\n l24\n-l25\n+L25\n l26\n l27\n")  # este de verdad no encaja
        self.parche("T-001-dos.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("dos.txt: 1 bloque no encaja", salida)
        self.assertIn("@@ -23,5 +23,5 @@", salida)
        self.assertNotIn("@@ -2,5 +2,5 @@", salida)

    def test_una_ruta_con_punto_punto_no_saca_nada_del_repo_ni_deja_copias(self):
        (self.base / "fuera.txt").write_bytes(b"secreto\n")  # al lado del repo, no dentro
        parche = ("diff --git a/../fuera.txt b/../fuera.txt\n--- a/../fuera.txt\n+++ b/../fuera.txt\n"
                  "@@ -1 +1 @@\n-secreto\n+cambiado\n")
        self.parche("T-001-fuera.patch", parche)
        temporal = self.base / "tmp"
        temporal.mkdir()
        with mock.patch.object(tempfile, "tempdir", str(temporal)):
            codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertIn("usa la ruta «../fuera.txt», que sale del repo", salida)
        self.assertEqual((self.base / "fuera.txt").read_bytes(), b"secreto\n")
        self.assertEqual(os.listdir(str(temporal)), [])  # ni se copió ni se escribió nada fuera de la copia

    def test_el_diagnostico_de_un_renombre_encuentra_el_archivo_de_origen(self):
        self.escribir("viejo.txt", "uno\ndos modificado\ntres\ncuatro\n")
        self.confirmar()
        parche = ("diff --git a/viejo.txt b/nuevo.txt\nsimilarity index 75%\nrename from viejo.txt\nrename to nuevo.txt\n"
                  "--- a/viejo.txt\n+++ b/nuevo.txt\n@@ -1,4 +1,4 @@\n uno\n-dos\n+DOS\n tres\n cuatro\n")
        self.parche("T-001-renombre.patch", parche)
        codigo, salida = self.correr()
        self.assertEqual(codigo, 1, salida)
        self.assertNotIn("no existe en tu repo", salida)
        self.assertIn("El parche esperaba:", salida)


class PruebaCopiaTemporal(unittest.TestCase):
    """La copia donde se diagnostica nunca lee de fuera del repo ni escribe fuera de sí misma."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="test-aplicar-"))
        self.addCleanup(borrar, self.base)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        escribir(self.repo / "a.txt", "dentro\n")
        escribir(self.base / "fuera.txt", "secreto\n")
        self.tmp = self.base / "tmp"
        self.tmp.mkdir()
        parche = mock.patch.object(tempfile, "tempdir", str(self.tmp))
        parche.start()
        self.addCleanup(parche.stop)

    @staticmethod
    def entrada(nombre):
        return (nombre, "1", "1", None)

    def test_copia_lo_que_existe_y_se_borra_al_salir(self):
        with ap._copia_temporal(self.repo, [self.entrada("a.txt"), self.entrada("nuevo.txt")]) as copia:
            self.assertEqual((copia / "a.txt").read_bytes(), b"dentro\n")
            self.assertFalse((copia / "nuevo.txt").exists())
        self.assertEqual(os.listdir(str(self.tmp)), [])

    def test_una_ruta_que_sale_del_repo_no_se_copia(self):
        with ap._copia_temporal(self.repo, [self.entrada("../fuera.txt")]) as copia:
            self.assertEqual(os.listdir(str(copia)), [])
            self.assertEqual(os.listdir(str(self.tmp)), [copia.name])

    def test_un_enlace_simbolico_que_apunta_fuera_del_repo_no_se_copia(self):
        try:
            os.symlink(str(self.base / "fuera.txt"), str(self.repo / "enlace.txt"))
        except (OSError, NotImplementedError, AttributeError):
            self.skipTest("este sistema no permite crear enlaces simbólicos")
        with ap._copia_temporal(self.repo, [self.entrada("enlace.txt")]) as copia:
            self.assertFalse((copia / "enlace.txt").exists())

    def test_una_ruta_cuyo_destino_saldria_de_la_copia_no_se_escribe(self):
        # «../repo/a.txt» es un archivo del repo, pero copiarlo dejaría un archivo fuera de la copia
        with ap._copia_temporal(self.repo, [self.entrada("../repo/a.txt")]) as copia:
            self.assertEqual(os.listdir(str(copia)), [])
            self.assertEqual(os.listdir(str(self.tmp)), [copia.name])

    def test_una_ruta_absoluta_no_se_copia_ni_se_pisa(self):
        victima = escribir(self.base / "victima.txt", "intacta\n")
        with ap._copia_temporal(self.repo, [self.entrada(str(victima))]) as copia:
            self.assertEqual(os.listdir(str(self.tmp)), [copia.name])
        self.assertEqual(victima.read_bytes(), b"intacta\n")

    def test_el_origen_de_un_renombre_tambien_se_copia(self):
        escribir(self.repo / "viejo.txt", "origen\n")
        with ap._copia_temporal(self.repo, [("nuevo.txt", "1", "1", "viejo.txt")]) as copia:
            self.assertEqual((copia / "viejo.txt").read_bytes(), b"origen\n")


class PruebaDesajuste(unittest.TestCase):
    def test_el_primer_desajuste_viene_despues_del_contexto_que_coincide(self):
        esperadas = ["a", "b", "c", "d", "e", "f", "g"]
        reales = ["x", "a", "b", "c", "D", "e", "f", "g", "y"]
        self.assertEqual(ap.localizar_desajuste(esperadas, reales, 1), (3, 4, False))

    def test_si_nada_coincide_se_usa_la_linea_del_encabezado(self):
        self.assertEqual(ap.localizar_desajuste(["zzz", "yyy"], ["a", "b", "c", "d", "e"], 3), (0, 2, False))

    def test_si_el_contexto_inicial_no_coincide_se_marca_desde_la_primera_linea(self):
        self.assertEqual(ap.localizar_desajuste(["MAL", "b", "c", "d"], ["a", "b", "c", "d", "e"], 1), (0, 0, False))

    def test_una_linea_en_blanco_suelta_no_sirve_de_ancla(self):
        # el blanco del inicio coincide con el primero del archivo, pero «a, b» está más abajo: manda «a, b»
        esperadas = ["", "a", "b", "c"]
        reales = ["", "w", "q", "r", "a", "b", "z"]
        self.assertEqual(ap.localizar_desajuste(esperadas, reales, 1), (0, 3, False))

    def test_solo_espacios_o_finales_de_linea(self):
        self.assertEqual(ap.localizar_desajuste(["a", "b"], ["a ", "b\r"], 1), (0, 0, True))

    def test_un_bloque_que_se_pasa_del_final_del_archivo(self):
        k, pos, solo = ap.localizar_desajuste(["a", "b", "c", "d"], ["a", "b"], 1)
        self.assertEqual((k, pos, solo), (2, 2, False))
        bloque = ap.Bloque("@@ -1,4 +1,4 @@", 1, [" a", " b", " c", "-d", "+D"])
        base = Path(tempfile.mkdtemp(prefix="test-aplicar-"))
        self.addCleanup(borrar, base)
        escribir(base / "f.txt", "a\nb\n")
        texto = "\n".join(ap.explicar_bloque(base, "f.txt", bloque))
        self.assertIn("(el archivo termina antes de esa línea)", texto)

    def test_leer_rechazos_separa_los_bloques_de_cada_archivo(self):
        base = Path(tempfile.mkdtemp(prefix="test-aplicar-"))
        self.addCleanup(borrar, base)
        escribir(base / "app" / "x.py.rej",
                 "diff a/app/x.py b/app/x.py\t(rejected hunks)\n"
                 "@@ -12,3 +12,3 @@\n uno\n-dos\n+DOS\n"
                 "@@ -30,2 +30,2 @@ def f():\n fin\n-viejo\n+nuevo\n")
        rechazos = ap.leer_rechazos(base)
        self.assertEqual(list(rechazos), ["app/x.py"])
        primero, segundo = rechazos["app/x.py"]
        self.assertEqual((primero.encabezado, primero.inicio), ("@@ -12,3 +12,3 @@", 12))
        self.assertEqual(primero.lineas, [" uno", "-dos", "+DOS"])
        self.assertEqual((segundo.encabezado, segundo.inicio), ("@@ -30,2 +30,2 @@", 30))
        self.assertEqual(ap._esperadas(segundo), ["fin", "viejo"])


# ---- modo estricto (D40) ----------------------------------------------------------------------------------------
class PruebaClasificarRojo(unittest.TestCase):
    def test_salidas_reales_de_pytest_y_unittest(self):
        casos = [
            ("pytest: NotImplementedError", 1, SALIDA_PYTEST_NOT_IMPLEMENTED, "correcto"),
            ("pytest: assert simple (sin la palabra AssertionError en la línea E)", 1, SALIDA_PYTEST_ASSERT, "correcto"),
            ("pytest: assert con --tb=no", 1, SALIDA_PYTEST_ASSERT_TB_NO, "correcto"),
            ("pytest: ImportError al importar", 2, SALIDA_PYTEST_IMPORT_ERROR, "incorrecto"),
            ("pytest: ModuleNotFoundError", 2, SALIDA_PYTEST_MODULE_NOT_FOUND, "incorrecto"),
            ("pytest: SyntaxError", 2, SALIDA_PYTEST_SINTAXIS, "incorrecto"),
            ("pytest: NameError sale con 1, igual que un rojo correcto", 1, SALIDA_PYTEST_NAME_ERROR, "incorrecto"),
            ("pytest: NameError con --tb=no", 1, SALIDA_PYTEST_NAME_ERROR_TB_NO, "incorrecto"),
            ("pytest: NameError con --tb=line", 1, SALIDA_PYTEST_NAME_ERROR_TB_LINE, "incorrecto"),
            ("unittest: errores y fallos juntos, todos buenos", 1, SALIDA_UNITTEST_MIXTA, "correcto"),
            ("unittest: ImportError al importar el módulo de tests", 1, SALIDA_UNITTEST_IMPORT, "incorrecto"),
            ("pytest: no encontró tests", 4, SALIDA_PYTEST_SIN_TESTS, "indeterminado"),
            ("unittest: ningún test", 5, SALIDA_UNITTEST_SIN_TESTS, "indeterminado"),
            ("unittest: AttributeError no está en la lista de D40", 1, SALIDA_ATTRIBUTE_ERROR, "indeterminado"),
        ]
        for nombre, codigo, salida, esperado in casos:
            with self.subTest(nombre):
                self.assertEqual(ap.clasificar_rojo(codigo, salida)[0], esperado)

    def test_el_detalle_nombra_las_excepciones(self):
        self.assertEqual(ap.clasificar_rojo(1, SALIDA_PYTEST_NOT_IMPLEMENTED), ("correcto", "NotImplementedError"))
        self.assertEqual(ap.clasificar_rojo(1, SALIDA_UNITTEST_MIXTA),
                         ("correcto", "AssertionError y NotImplementedError"))
        self.assertEqual(ap.clasificar_rojo(1, SALIDA_PYTEST_ASSERT_TB_NO),
                         ("correcto", "una aserción que no se cumple"))
        self.assertEqual(ap.clasificar_rojo(2, SALIDA_PYTEST_MODULE_NOT_FOUND),
                         ("incorrecto", "ImportError, ModuleNotFoundError"))

    def test_si_los_tests_pasan_no_es_un_rojo(self):
        self.assertEqual(ap.clasificar_rojo(0, "..\nRan 2 tests in 0.001s\n\nOK\n"), ("paso", ""))

    def test_una_marca_mala_gana_a_una_buena(self):
        salida = SALIDA_UNITTEST_MIXTA + "\n" + SALIDA_UNITTEST_IMPORT
        self.assertEqual(ap.clasificar_rojo(1, salida)[0], "incorrecto")

    def test_indentationerror_y_taberror_son_errores_de_sintaxis(self):
        for nombre in ("IndentationError: unexpected indent", "TabError: inconsistent use of tabs and spaces"):
            with self.subTest(nombre):
                salida = "Traceback (most recent call last):\n  File \"x.py\", line 3\n" + nombre + "\n"
                self.assertEqual(ap.clasificar_rojo(1, salida)[0], "incorrecto")

    def test_un_nombre_de_test_con_el_nombre_de_una_excepcion_no_confunde(self):
        salida = ("F\nFAILED test_x.py::test_no_lanza_NameError - AssertionError: 1 != 2\n"
                  "test_x.py:5: AssertionError\n")
        self.assertEqual(ap.clasificar_rojo(1, salida), ("correcto", "AssertionError"))

    def test_un_codigo_de_salida_sin_marcas_es_indeterminado(self):
        veredicto, detalle = ap.clasificar_rojo(3, "algo raro pasó\n")
        self.assertEqual(veredicto, "indeterminado")
        self.assertIn("salió con 3", detalle)


class PruebaEstricto(PruebaConGit):
    def preparar(self, calc, test=TEST_CALC, nombre="T-010-tests.patch"):
        parche = (parche_archivo_nuevo("calc.py", calc) if calc is not None else "") \
            + parche_archivo_nuevo("test_calc.py", test)
        return self.parche(nombre, parche)

    def test_rojo_correcto_por_not_implemented_error(self):
        self.preparar(CALC_ESQUELETO)
        codigo, salida = self.correr(estricto=COMANDO_UNITTEST)
        self.assertEqual(codigo, 0, salida)
        self.assertIn("Rojo CORRECTO: el test falla por NotImplementedError", salida)
        self.assertIn("Modo estricto (D40)", salida)

    def test_rojo_correcto_por_una_asercion_que_no_se_cumple(self):
        self.preparar(CALC_CERO)
        codigo, salida = self.correr(estricto=COMANDO_UNITTEST)
        self.assertEqual(codigo, 0, salida)
        self.assertIn("Rojo CORRECTO: el test falla por AssertionError", salida)

    def test_rojo_incorrecto_si_falta_el_esqueleto(self):
        self.preparar(None)
        codigo, salida = self.correr(estricto=COMANDO_UNITTEST)
        self.assertEqual(codigo, 1, salida)
        self.assertIn("Rojo INCORRECTO", salida)
        self.assertIn("ModuleNotFoundError", salida)
        self.assertIn("aplicado sin guardar", salida)
        self.assertTrue((self.repo / "test_calc.py").exists())  # el programa no revierte nada

    def test_rojo_incorrecto_por_un_error_de_sintaxis(self):
        self.preparar(CALC_ESQUELETO, test="import unittest\nfrom calc import sumar\n\ndef test_x(:\n    pass\n")
        codigo, salida = self.correr(estricto=COMANDO_UNITTEST)
        self.assertEqual(codigo, 1, salida)
        self.assertIn("Rojo INCORRECTO", salida)
        self.assertIn("SyntaxError", salida)

    def test_rojo_incorrecto_por_un_nombre_que_no_existe(self):
        test = ("import unittest\n\n\nclass T(unittest.TestCase):\n    def test_x(self):\n"
                "        self.assertEqual(variable_inexistente, 1)\n")
        self.preparar(CALC_ESQUELETO, test=test)
        codigo, salida = self.correr(estricto=COMANDO_UNITTEST)
        self.assertEqual(codigo, 1, salida)
        self.assertIn("NameError", salida)

    def test_si_los_tests_pasan_es_un_error_en_el_parche_1(self):
        self.preparar(CALC_BIEN)
        codigo, salida = self.correr(estricto=COMANDO_UNITTEST)
        self.assertEqual(codigo, 1, salida)
        self.assertIn("Los tests PASARON", salida)

    def test_una_razon_que_no_se_reconoce_es_indeterminada_y_da_1(self):
        test = TEST_CALC.replace("from calc import sumar\n", "import calc\n").replace("sumar(1, 2)", "calc.sumar(1, 2)")
        self.preparar("x = 1\n", test=test)
        codigo, salida = self.correr(estricto=COMANDO_UNITTEST)
        self.assertEqual(codigo, 1, salida)
        self.assertIn("No pude confirmar la razón del rojo", salida)
        self.assertIn("AttributeError", salida)  # la salida del test se muestra para que lo lea la persona

    def test_si_el_parche_no_aplica_no_se_corre_el_test(self):
        escribir(self.repo / "marca.py", "open('corrio.txt', 'w').close()\n")
        self.escribir("a.txt", ARCHIVO_A.replace("cuatro", "otra-cosa"))
        self.confirmar()
        self.parche("T-001-a.patch", PARCHE_A)
        codigo, salida = self.correr(estricto='"%s" marca.py' % sys.executable)
        self.assertEqual(codigo, 1, salida)
        self.assertNotIn("Modo estricto", salida)
        self.assertFalse((self.repo / "corrio.txt").exists())

    def test_con_check_no_se_corre_el_test(self):
        escribir(self.repo / "marca.py", "open('corrio.txt', 'w').close()\n")
        self.preparar(CALC_ESQUELETO)
        codigo, salida = self.correr(estricto='"%s" marca.py' % sys.executable, solo_check=True)
        self.assertEqual(codigo, 0, salida)
        self.assertIn("Con --check no se corre el comando de test", salida)
        self.assertFalse((self.repo / "corrio.txt").exists())

    def test_el_test_corre_en_la_raiz_aunque_se_invoque_desde_una_subcarpeta(self):
        self.escribir("sub/otro.txt", "x\n")
        escribir(self.repo / "donde.py", "import os\nopen('donde.txt', 'w').write(os.getcwd())\n")
        self.confirmar()
        self.preparar(CALC_ESQUELETO)
        self.correr(estricto='"%s" donde.py' % sys.executable, cwd=self.repo / "sub")
        escrito = (self.repo / "donde.txt").read_text(encoding="utf-8")
        self.assertTrue(os.path.samefile(escrito, str(self.repo)), escrito)

    def test_la_salida_del_test_con_acentos_no_se_rompe(self):
        escribir(self.repo / "rojo.py", "raise NotImplementedError('sumar áéíóú ñ')\n")
        self.preparar(CALC_ESQUELETO)
        codigo, salida = self.correr(estricto='"%s" rojo.py' % sys.executable)
        self.assertEqual(codigo, 0, salida)
        self.assertIn("sumar áéíóú ñ", salida)

    def test_con_mucha_salida_muestra_solo_el_final(self):
        escribir(self.repo / "ruidoso.py",
                 "for i in range(100):\n    print('linea de ruido', i)\nraise NotImplementedError('fin')\n")
        self.preparar(CALC_ESQUELETO)
        codigo, salida = self.correr(estricto='"%s" ruidoso.py' % sys.executable)
        self.assertEqual(codigo, 0, salida)
        self.assertIn("líneas más arriba", salida)
        self.assertNotIn("linea de ruido 0\n", salida)
        self.assertIn("NotImplementedError: fin", salida)


# ---- D45: nunca guarda nada en git y declara la codificación ----------------------------------------------------------
def _cadena(nodo):
    """El valor de un literal de texto en el árbol (en Python 3.7 son ast.Str; después, ast.Constant)."""
    tipo = type(nodo).__name__
    if tipo == "Constant" and isinstance(nodo.value, str):
        return nodo.value
    if tipo == "Str":
        return nodo.s
    return None


def _llamadas_a(arbol, nombre):
    return [n for n in ast.walk(arbol) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == nombre]


class PruebaEstatica(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codigo = FUENTE.read_text(encoding="utf-8")
        cls.arbol = ast.parse(cls.codigo)

    def test_codificacion_utf8_estatica(self):
        for nodo in ast.walk(self.arbol):
            if not isinstance(nodo, ast.Call):
                continue
            f = nodo.func
            nombre = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
            claves = {k.arg for k in nodo.keywords}
            donde = "línea %d" % nodo.lineno
            if nombre == "open":
                modo = _cadena(nodo.args[1]) if len(nodo.args) > 1 else None
                for k in nodo.keywords:
                    if k.arg == "mode":
                        modo = _cadena(k.value)
                modo = modo or "r"
                if "b" in modo:
                    continue
                self.assertIn("encoding", claves, "open() sin encoding en la " + donde)
                if "w" in modo or "a" in modo:
                    self.assertIn("newline", claves, "open() de escritura sin newline en la " + donde)
            elif nombre in ("read_text", "write_text"):
                self.fail("%s() en la %s: usa open(..., encoding=...) (write_text no acepta newline antes de 3.10)"
                          % (nombre, donde))
            elif nombre in ("run", "check_output", "Popen"):
                texto = any(k.arg in ("text", "universal_newlines") for k in nodo.keywords)
                if texto:
                    self.assertIn("encoding", claves, "subprocess con text=True sin encoding en la " + donde)

    def test_no_usa_sintaxis_ni_funciones_posteriores_a_python_37(self):
        prohibidos = {"removeprefix", "removesuffix", "is_relative_to", "with_stem", "readlink", "fromisoformat_x"}
        claves_nuevas = {"missing_ok", "dirs_exist_ok", "newline_x"}
        for nodo in ast.walk(self.arbol):
            tipo = type(nodo).__name__
            self.assertNotIn(tipo, ("NamedExpr", "Match"), "sintaxis de Python 3.8+ en la línea %d" % getattr(nodo, "lineno", 0))
            if isinstance(nodo, ast.Attribute):
                self.assertNotIn(nodo.attr, prohibidos, "método de Python 3.9+ en la línea %d" % nodo.lineno)
            if isinstance(nodo, ast.keyword):
                self.assertNotIn(nodo.arg, claves_nuevas, "argumento de Python 3.8+: %s" % nodo.arg)
            if isinstance(nodo, ast.arguments):
                self.assertEqual(getattr(nodo, "posonlyargs", []), [], "parámetros solo posicionales (3.8+)")

    def test_solo_importa_la_biblioteca_estandar(self):
        estandar = set(getattr(sys, "stdlib_module_names", ())) or {
            "argparse", "contextlib", "difflib", "json", "os", "re", "shutil", "subprocess", "sys", "tempfile",
            "time", "collections", "pathlib"}
        for nodo in ast.walk(self.arbol):
            if isinstance(nodo, ast.Import):
                modulos = [a.name.split(".")[0] for a in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                modulos = [(nodo.module or "").split(".")[0]]
            else:
                continue
            for m in modulos:
                self.assertIn(m, estandar, "«%s» no es de la biblioteca estándar" % m)

    def test_cada_llamada_a_git_usa_solo_la_lista_blanca(self):
        llamadas = _llamadas_a(self.arbol, "_git")
        self.assertGreater(len(llamadas), 5)
        for nodo in llamadas:
            sub = _cadena(nodo.args[1]) if len(nodo.args) > 1 else None
            self.assertIn(sub, ap.PERMITIDOS, "git %r no está en la lista blanca (línea %d)" % (sub, nodo.lineno))
            for arg in nodo.args[2:]:
                valor = _cadena(arg)
                if valor is not None and valor.startswith("-"):
                    self.assertIn(valor, ap.PERMITIDOS[sub], "git %s %s no está permitido (línea %d)" % (sub, valor, nodo.lineno))

    def test_nunca_aparecen_las_opciones_ni_los_comandos_que_guardan(self):
        prohibidas = {"--index", "--cached", "--3way", "-3", "add", "commit", "stash", "reset", "checkout", "push",
                      "rm", "clean", "restore", "merge", "rebase", "cherry-pick", "revert", "tag", "branch", "config"}
        for nodo in ast.walk(self.arbol):
            valor = _cadena(nodo)
            if valor is not None:
                self.assertNotIn(valor, prohibidas, "«%s» no puede aparecer en este programa" % valor)

    def test_el_codigo_ejecuta_procesos_solo_desde_git_y_correr_prueba(self):
        sitios = set()
        for funcion in [n for n in ast.walk(self.arbol) if isinstance(n, ast.FunctionDef)]:
            for nodo in ast.walk(funcion):
                if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
                    if isinstance(nodo.func.value, ast.Name) and nodo.func.value.id == "subprocess":
                        sitios.add(funcion.name)
                    if isinstance(nodo.func.value, ast.Name) and nodo.func.value.id == "os" and nodo.func.attr in (
                            "system", "popen", "remove", "unlink", "rmdir", "removedirs"):
                        sitios.add(funcion.name + ":os." + nodo.func.attr)
        self.assertEqual(sitios, {"_git", "correr_prueba", "_parche_temporal:os.remove"})


class PruebaListaBlanca(PruebaConGit):
    def test_git_rechaza_todo_lo_que_guarda_o_cambia_el_historial(self):
        comandos = [("add", "-A"), ("commit", "-m", "x"), ("stash",), ("reset", "--hard"), ("checkout", "--", "."),
                    ("push",), ("rm", "a.txt"), ("clean", "-fd"), ("config", "user.name", "x"),
                    ("apply", "--index", "x.patch"), ("apply", "--cached", "x.patch"), ("apply", "--3way", "x.patch"),
                    ("rev-parse", "--git-dir"), ("status", "--porcelain")]
        for comando in comandos:
            with self.subTest(comando=comando):
                with self.assertRaises(ap.GitError):
                    ap._git(self.repo, *comando)

    def test_reject_solo_se_permite_sobre_una_copia(self):
        with self.assertRaises(ap.GitError) as ctx:
            ap._git(self.repo, "apply", "--reject", "x.patch")
        self.assertIn("copia temporal", str(ctx.exception))
        copia = self.base / "copia"
        copia.mkdir()
        ap._git(copia, "apply", "--reject", "no-existe.patch", en_copia=True)  # no lanza GitError

    def test_aplicar_y_diagnosticar_no_cambian_head_indice_ni_stash(self):
        self.escribir("a.txt", ARCHIVO_A)
        self.confirmar()
        head = self.git("rev-parse", "HEAD")
        self.parche("T-001-a.patch", PARCHE_A)
        self.assertEqual(self.correr()[0], 0)
        self.parche("T-002-malo.patch", PARCHE_B)
        self.assertEqual(self.correr()[0], 1)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "")
        self.assertEqual(self.git("stash", "list"), "")
        self.assertEqual(self.estado(), " M a.txt\n")

    def test_si_git_no_esta_instalado_es_un_error_de_entorno(self):
        with mock.patch.object(ap.subprocess, "run", side_effect=FileNotFoundError(2, "No such file or directory")):
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                codigo = ap.ejecutar(None, None, False, cwd=self.repo, home=self.home)
        self.assertEqual(codigo, 2)
        self.assertIn("no pude correr git", salida.getvalue())

    def test_fuera_de_un_repo_da_2_y_dice_que_hacer(self):
        fuera = self.base / "fuera"
        fuera.mkdir()
        with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(self.base)}):
            codigo, salida = self.correr(cwd=fuera)
        self.assertEqual(codigo, 2)
        self.assertIn("no está dentro de un repo de git", salida)


# ---- línea de comandos ------------------------------------------------------------------------------------------------
class PruebaCLI(PruebaConGit):
    def setUp(self):
        super().setUp()
        self.escribir("a.txt", ARCHIVO_A)
        self.confirmar()

    def texto(self, r):
        return (r.stdout + r.stderr).decode("utf-8", errors="replace")

    def test_ayuda(self):
        r = self.correr_cli("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--estricto", self.texto(r))
        self.assertIn("--check", self.texto(r))

    def test_una_opcion_desconocida_da_2(self):
        self.assertEqual(self.correr_cli("--no-existe").returncode, 2)

    def test_estricto_sin_comando_da_2(self):
        self.parche("T-001-a.patch", PARCHE_A)
        self.assertEqual(self.correr_cli("--estricto", "").returncode, 2)
        self.assertEqual(self.leer("a.txt"), ARCHIVO_A.encode("utf-8"))

    def test_codigos_de_salida(self):
        self.parche("T-001-a.patch", PARCHE_A)
        self.assertEqual(self.correr_cli().returncode, 0)  # aplica
        self.assertEqual(self.correr_cli().returncode, 1)  # ya estaba aplicado
        self.assertEqual(self.correr_cli("no-existe.patch").returncode, 2)

    def test_el_parche_se_pasa_como_argumento(self):
        ruta = self.parche("T-001-a.patch", PARCHE_A)
        r = self.correr_cli(str(ruta))
        self.assertEqual(r.returncode, 0, self.texto(r))
        self.assertEqual(self.leer("a.txt"), ARCHIVO_A_DESPUES.encode("utf-8"))

    def test_el_modo_estricto_por_linea_de_comandos(self):
        parche = parche_archivo_nuevo("calc.py", CALC_ESQUELETO) + parche_archivo_nuevo("test_calc.py", TEST_CALC)
        ruta = self.parche("T-010-tests.patch", parche)
        r = self.correr_cli(str(ruta), "--estricto", COMANDO_UNITTEST)
        self.assertEqual(r.returncode, 0, self.texto(r))
        self.assertIn("Rojo CORRECTO", self.texto(r))

    def test_una_consola_cp1252_no_tumba_el_programa(self):
        # D45: la consola de Windows puede no poder escribir el nombre de un archivo; se reemplaza, no se cae
        self.parche("T-001-japones.patch", parche_archivo_nuevo("日本.txt", "hola\n"))
        r = self.correr_cli(entorno={"PYTHONIOENCODING": "cp1252"})
        self.assertEqual(r.returncode, 0, r.stdout.decode("cp1252", errors="replace") + r.stderr.decode("cp1252", errors="replace"))
        self.assertIn(b"Aplicado", r.stdout)


if __name__ == "__main__":
    unittest.main()
