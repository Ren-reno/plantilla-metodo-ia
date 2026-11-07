"""Pruebas de tools/comprobar.py. Solo usan la biblioteca estándar.

Correr desde la raíz del repo:
    python -m unittest discover -s tools/tests -v

El grupo «VerdesFalsos» reproduce los cinco casos del piloto en que una entrega
pasó las compuertas del método siendo falsa, y comprueba que ahora fallan.
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

import comprobar as co  # noqa: E402

PRUEBA_QUE_PASA = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n"
PRUEBA_QUE_FALLA = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_no(self):\n        self.assertTrue(False)\n"
UNITTEST = ["python", "-B", "-m", "unittest", "discover", "-s", "tests"]


def config(**cambios) -> dict:
    base = {
        "version": 1,
        "distribucion": "solo-yo",
        "plataformas": [],
        "stacks": {"python": {"pruebas": UNITTEST}},
        "comandos": {},
        "excepciones": [],
    }
    base.update(cambios)
    return base


class Repo:
    """Un repo de mentira para probar comprobar.py como módulo y por línea de comandos."""

    def __init__(self, test, cfg: dict | None = None):
        self.dir = Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, self.dir, True)
        (self.dir / "tools").mkdir()
        shutil.copy(TOOLS / "comprobar.py", self.dir / "tools" / "comprobar.py")
        if cfg is not None:
            self.config(cfg)

    def config(self, cfg: dict):
        self.poner(co.REL_CONFIG, json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")

    def poner(self, rel: str, texto: str):
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8", newline="\n")

    def con_prueba_que_pasa(self):
        self.poner("tests/test_humo.py", PRUEBA_QUE_PASA)
        return self

    def correr(self, *args):
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        return subprocess.run([sys.executable, str(self.dir / "tools" / "comprobar.py"), *args],
                              cwd=self.dir, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=entorno)

    def contexto(self, timeout: int = 120) -> co.Contexto:
        cfg = co.cargar_config(self.dir)
        return co.Contexto(self.dir, cfg, sys.executable, self.dir / co.REL_LOGS / "prueba", timeout)

    def paso(self, nombre: str, stack: str = "", timeout: int = 120) -> dict:
        return co.PASOS[nombre](self.contexto(timeout), stack)


# ---- configuración -------------------------------------------------------------------------------
class Configuracion(unittest.TestCase):
    def test_sin_config_no_inventa_comandos_y_devuelve_2(self):
        r = Repo(self)
        p = r.correr("rapido")
        self.assertEqual(p.returncode, 2)
        self.assertIn("No existe comprobaciones.json", p.stdout)
        self.assertIn("--ejemplo", p.stdout)

    def test_el_ejemplo_que_imprime_es_una_config_valida(self):
        r = Repo(self)
        p = r.correr("--ejemplo")
        self.assertEqual(p.returncode, 0)
        r.poner(co.REL_CONFIG, p.stdout)
        self.assertEqual(co.cargar_config(r.dir)["distribucion"], "solo-yo")

    def test_json_invalido_version_y_distribucion_se_rechazan(self):
        r = Repo(self)
        r.poner(co.REL_CONFIG, "{no es json")
        self.assertEqual(r.correr("rapido").returncode, 2)
        r.config(config(version=2))
        self.assertIn("«version» debe ser 1", r.correr("rapido").stdout)
        r.config(config(distribucion="cuando-quiera"))
        self.assertIn("«distribucion» debe ser uno de", r.correr("rapido").stdout)

    def test_un_stack_necesita_su_comando_de_pruebas(self):
        r = Repo(self, config(stacks={"python": {}}))
        self.assertIn("necesita «pruebas» como lista", r.correr("rapido").stdout)
        r.config(config(stacks={}))
        self.assertIn("al menos un stack", r.correr("rapido").stdout)

    def test_una_excepcion_necesita_paso_y_motivo(self):
        r = Repo(self, config(excepciones=[{"paso": "pruebas:js"}]))
        self.assertIn("cada excepción necesita «paso» y «motivo»", r.correr("rapido").stdout)

    def test_perfil_inexistente_devuelve_2_y_lista_los_que_hay(self):
        r = Repo(self, config())
        p = r.correr("completo")
        self.assertEqual(p.returncode, 2)
        self.assertIn("rapido", p.stdout)
        self.assertIn("entrega", p.stdout)

    def test_los_perfiles_se_abren_por_stack(self):
        cfg = config(stacks={"python": {"pruebas": UNITTEST}, "js": {"pruebas": ["node", "--test"]}})
        self.assertEqual(co.pasos_del_perfil(cfg, "rapido"), ["plan", "pruebas:js", "pruebas:python"])

    def test_listar_muestra_configuracion_y_pasos(self):
        r = Repo(self, config(comandos={"arrancar": "python -m http.server"}))
        p = r.correr("--listar")
        self.assertEqual(p.returncode, 0)
        self.assertIn("Perfil «entrega»", p.stdout)
        self.assertIn("python -m http.server", p.stdout)


# ---- los cinco verdes falsos del piloto ----------------------------------------------------------
class VerdesFalsos(unittest.TestCase):
    def test_1_un_comando_que_sale_bien_sin_ejecutar_pruebas_falla(self):
        # El caso de npm test devolviendo 0 sin encontrar pruebas (H-29).
        r = Repo(self, config(stacks={"js": {"pruebas": ["python", "-c", "print('no hay pruebas')"]}}))
        res = r.paso("pruebas", "js")
        self.assertEqual(res["estado"], co.FALLO)
        self.assertIn("no pude contar pruebas ejecutadas", res["detalle"])
        self.assertEqual(r.correr("rapido").returncode, 1)

    def test_1b_cero_pruebas_ejecutadas_falla_con_el_numero_a_la_vista(self):
        # Un corredor que informa cero y sale bien: el caso que más se parece a un verde.
        cfg = config(stacks={"python": {"pruebas": ["python", "-c", "print('Ran 0 tests in 0.000s')"]}})
        r = Repo(self, cfg)
        res = r.paso("pruebas", "python")
        self.assertEqual(res["estado"], co.FALLO)
        self.assertIn("0 pruebas", res["detalle"])

    def test_1c_una_carpeta_de_pruebas_vacia_falla_con_cualquier_corredor(self):
        # unittest informa «NO TESTS RAN» y pytest sale con 5: ninguno debe pasar por verde.
        r = Repo(self, config())
        r.poner("tests/__init__.py", "")
        self.assertEqual(r.paso("pruebas", "python")["estado"], co.FALLO)

    def test_2_dependencias_sin_fijar_no_son_instalacion_reproducible(self):
        # El caso de requirements.txt con >= presentado como reproducible (H-29).
        cfg = config(stacks={"python": {"pruebas": UNITTEST, "dependencias": ["requirements.txt"],
                                        "fijadas": True}})
        r = Repo(self, cfg)
        r.poner("requirements.txt", "# comentario\nfastapi>=0.1\nuvicorn==0.54.0\n-r otro.txt\n")
        res = r.paso("dependencias", "python")
        self.assertEqual(res["estado"], co.FALLO)
        self.assertIn("1 sin fijar", res["detalle"])
        self.assertIn("fastapi>=0.1", res["detalle"])

        r.poner("requirements.txt", "fastapi==0.162.0\nuvicorn==0.54.0\n")
        self.assertEqual(r.paso("dependencias", "python")["estado"], co.OK)

    def test_2b_un_archivo_de_dependencias_declarado_y_ausente_falla(self):
        cfg = config(stacks={"python": {"pruebas": UNITTEST, "dependencias": ["package-lock.json"]}})
        r = Repo(self, cfg)
        res = r.paso("dependencias", "python")
        self.assertEqual(res["estado"], co.FALLO)
        self.assertIn("falta package-lock.json", res["detalle"])

    def test_3_un_comando_documentado_que_cita_un_modulo_inexistente_falla(self):
        # El caso de uvicorn src.app.web:app, documentado sin existir (H-29, seguimiento):
        # el repo tiene src/, pero no ese módulo.
        r = Repo(self, config(comandos={"arrancar": "python -m http.server src.app.web:app"}))
        r.poner("src/app/main.py", "x = 1\n")
        res = r.paso("comandos")
        self.assertEqual(res["estado"], co.FALLO)
        self.assertIn("src.app.web", res["detalle"])

    def test_3b_un_comando_cuyo_modulo_existe_pasa(self):
        r = Repo(self, config(comandos={"arrancar": "python -m http.server"}))
        self.assertEqual(r.paso("comandos")["estado"], co.OK)

    def test_3c_un_modulo_propio_del_repo_se_localiza_sin_importarlo(self):
        r = Repo(self, config(comandos={"arrancar": "python -m http.server src.app.web:app"}))
        r.poner("src/app/web.py", "raise SystemExit('esto no debe ejecutarse al comprobar')\n")
        self.assertEqual(r.paso("comandos")["estado"], co.OK)

    def test_3e_un_modulo_de_terceros_sin_instalar_se_informa_pero_no_falla(self):
        # comprobar.py no instala nada: que una dependencia no esté aquí no es
        # documentación equivocada. Lo dice y sigue; «dependencias» cubre lo otro.
        r = Repo(self, config(comandos={"arrancar": "python -m paquete_que_no_existe_xyz"}))
        res = r.paso("comandos")
        self.assertEqual(res["estado"], co.OK)
        self.assertIn("no está instalado aquí", res["detalle"])
        self.assertIn("paquete_que_no_existe_xyz", res["detalle"])

    def test_3d_un_comando_pendiente_no_pasa_como_declarado(self):
        r = Repo(self, config(comandos={"instalar": "(pendiente)"}))
        res = r.paso("comandos")
        self.assertEqual(res["estado"], co.FALLO)
        self.assertIn("(pendiente)", res["detalle"])

    def test_4_una_plataforma_declarada_que_el_CI_no_corre_falla(self):
        # Hermano del caso de la grafía: lo declarado debe ejecutarse en alguna parte (H-30).
        cfg = config(distribucion="otras-personas", plataformas=["ubuntu-24.04 · python-3.12",
                                                                 "windows-2022 · python-3.12"])
        r = Repo(self, cfg)
        r.poner(co.REL_CI, "jobs:\n  checks:\n    runs-on: ubuntu-24.04\n    # python-3.12\n")
        res = r.paso("plataformas")
        self.assertEqual(res["estado"], co.FALLO)
        self.assertIn("windows-2022", res["detalle"])

    def test_4b_sin_CI_o_sin_plataformas_declaradas_falla_al_distribuir(self):
        r = Repo(self, config(distribucion="otras-personas", plataformas=["ubuntu-24.04"]))
        self.assertIn(co.REL_CI, r.paso("plataformas")["detalle"])
        r.config(config(distribucion="otras-personas", plataformas=[]))
        self.assertIn("no declaraste plataformas", r.paso("plataformas")["detalle"])

    def test_5_sin_version_de_producto_no_se_sabe_donde_aparece_un_fallo(self):
        # En cuanto el software vive en dos sitios hace falta saber cuál es cuál.
        r = Repo(self, config(distribucion="mis-dispositivos"))
        self.assertEqual(r.paso("version")["estado"], co.FALLO)
        r.poner("pyproject.toml", '[project]\nname = "x"\nversion = "0.1.0"\n')
        self.assertEqual(r.paso("version")["estado"], co.OK)
        r.poner("package.json", '{"name": "x", "version": "0.2.0"}\n')
        res = r.paso("version")
        self.assertEqual(res["estado"], co.FALLO)
        self.assertIn("no coinciden", res["detalle"])


# ---- pasos ---------------------------------------------------------------------------------------
class Pasos(unittest.TestCase):
    def test_pruebas_que_pasan_reportan_cuantas_corrieron(self):
        r = Repo(self, config()).con_prueba_que_pasa()
        res = r.paso("pruebas", "python")
        self.assertEqual(res["estado"], co.OK)
        self.assertIn("1 pruebas", res["detalle"])

    def test_pruebas_que_fallan_fallan_con_el_resumen_del_corredor(self):
        r = Repo(self, config())
        r.poner("tests/test_no.py", PRUEBA_QUE_FALLA)
        res = r.paso("pruebas", "python")
        self.assertEqual(res["estado"], co.FALLO)
        self.assertTrue(res["detalle"])

    def test_timeout_no_se_confunde_con_fallo_de_prueba(self):
        cfg = config(stacks={"python": {"pruebas": ["python", "-c", "import time; time.sleep(5)"]}})
        r = Repo(self, cfg)
        self.assertEqual(r.paso("pruebas", "python", timeout=1)["estado"], co.TIMEOUT)

    def test_una_excepcion_declarada_no_es_verde_pero_no_frena(self):
        cfg = config(stacks={"js": {"pruebas": ["python", "-c", "print('sin frontend todavia')"]}},
                     excepciones=[{"paso": "pruebas:js", "motivo": "aún no hay frontend",
                                   "hasta": "T-008", "fecha": "2026-11-06"}])
        r = Repo(self, cfg)
        res = r.paso("pruebas", "js")
        self.assertEqual(res["estado"], co.EXCEPCION)
        self.assertIn("aún no hay frontend", res["detalle"])
        self.assertIn("T-008", res["detalle"])
        p = r.correr("rapido")
        self.assertEqual(p.returncode, 0)
        self.assertIn("deuda declarada", p.stdout)

    def test_plan_se_omite_sin_validador_o_sin_backlog(self):
        r = Repo(self, config())
        self.assertEqual(r.paso("plan")["estado"], co.OMITIDO)
        shutil.copy(TOOLS / "validar.py", r.dir / "tools" / "validar.py")
        res = r.paso("plan")
        self.assertEqual(res["estado"], co.OMITIDO)
        self.assertIn(co.REL_BACKLOG, res["detalle"])

    def test_licencia_solo_se_exige_al_distribuir_a_terceros(self):
        r = Repo(self, config(distribucion="mis-dispositivos"))
        self.assertEqual(r.paso("licencia")["estado"], co.OMITIDO)
        r.config(config(distribucion="otras-personas"))
        self.assertEqual(r.paso("licencia")["estado"], co.FALLO)
        r.poner("LICENSE", "MIT\n")
        self.assertEqual(r.paso("licencia")["estado"], co.OK)

    def test_plataformas_se_omiten_si_el_software_no_sale_de_tu_maquina(self):
        r = Repo(self, config(distribucion="solo-yo", plataformas=["lo-que-sea"]))
        self.assertEqual(r.paso("plataformas")["estado"], co.OMITIDO)

    def test_version_se_omite_mientras_solo_exista_tu_copia(self):
        r = Repo(self, config(distribucion="solo-yo"))
        self.assertEqual(r.paso("version")["estado"], co.OMITIDO)

    def test_ruta_prueba_solo_lo_que_pide_la_tarjeta(self):
        cfg = config(stacks={"python": {"pruebas": UNITTEST,
                                        "pruebas_una": ["python", "-B", "-m", "unittest", "discover",
                                                        "-s", "{ruta}"]}})
        r = Repo(self, cfg)
        r.poner("tests/uno/test_a.py", PRUEBA_QUE_PASA)
        r.poner("tests/dos/test_b.py", PRUEBA_QUE_FALLA)
        ctx = r.contexto()
        ctx.ruta = "tests/uno"
        self.assertEqual(co.paso_pruebas(ctx, "python")["estado"], co.OK)
        ctx.ruta = "tests/dos"
        self.assertEqual(co.paso_pruebas(ctx, "python")["estado"], co.FALLO)

    def test_sin_pruebas_una_declaradas_corre_todo_y_lo_dice(self):
        r = Repo(self, config()).con_prueba_que_pasa()
        ctx = r.contexto()
        ctx.ruta = "tests/libros"
        res = co.paso_pruebas(ctx, "python")
        self.assertEqual(res["estado"], co.OK)
        self.assertIn("suite completa", res["detalle"])

    def test_pruebas_una_mal_declarada_se_rechaza(self):
        r = Repo(self, config(stacks={"python": {"pruebas": UNITTEST, "pruebas_una": "pytest {ruta}"}}))
        self.assertIn("«pruebas_una»", r.correr("rapido").stdout)

    def test_herramientas_se_omite_cuando_el_repo_no_las_trae(self):
        r = Repo(self, config())
        self.assertEqual(r.paso("herramientas")["estado"], co.OMITIDO)


# ---- línea de comandos ---------------------------------------------------------------------------
class LineaDeComandos(unittest.TestCase):
    def test_todo_en_verde_devuelve_0_y_lo_dice(self):
        r = Repo(self, config()).con_prueba_que_pasa()
        p = r.correr("rapido")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("Comprobación superada", p.stdout)
        self.assertIn("probó algo", p.stdout)

    def test_un_paso_fallido_devuelve_1_y_nombra_los_pasos(self):
        r = Repo(self, config())
        r.poner("tests/test_no.py", PRUEBA_QUE_FALLA)
        p = r.correr("rapido")
        self.assertEqual(p.returncode, 1)
        self.assertIn("Comprobación fallida", p.stdout)
        self.assertIn("pruebas:python", p.stdout)

    def test_un_paso_inexistente_en_el_perfil_se_reporta_sin_romperse(self):
        r = Repo(self, config(perfiles={"rapido": ["inventado"]}))
        p = r.correr("rapido")
        self.assertEqual(p.returncode, 1)
        self.assertIn("no existe el paso", p.stdout)

    def test_un_stack_inexistente_en_el_perfil_se_reporta(self):
        r = Repo(self, config(perfiles={"rapido": ["pruebas:rust"]}))
        p = r.correr("rapido")
        self.assertEqual(p.returncode, 1)
        self.assertIn("rust", p.stdout)

    def test_guarda_los_logs_completos_en_disco(self):
        r = Repo(self, config()).con_prueba_que_pasa()
        p = r.correr("rapido")
        self.assertIn(co.REL_LOGS, p.stdout)
        logs = list((r.dir / co.REL_LOGS).rglob("pruebas-python.log"))
        self.assertEqual(len(logs), 1, "cada paso ejecutado deja su log")
        texto = logs[0].read_text(encoding="utf-8")
        self.assertIn("# paso: pruebas:python", texto)
        self.assertIn("Ran 1 test", texto)

    def test_no_modifica_el_repo_mas_alla_de_sus_logs(self):
        r = Repo(self, config()).con_prueba_que_pasa()
        antes = {p.relative_to(r.dir).as_posix() for p in r.dir.rglob("*") if p.is_file()}
        r.correr("rapido")
        despues = {p.relative_to(r.dir).as_posix() for p in r.dir.rglob("*") if p.is_file()}
        nuevos = {p for p in despues - antes if not p.startswith(co.REL_LOGS)}
        self.assertEqual(nuevos, set(), f"no debería escribir nada más: {nuevos}")

    def test_un_interprete_inexistente_devuelve_2(self):
        r = Repo(self, config())
        p = r.correr("rapido", "--python", str(r.dir / "no-existe.exe"))
        self.assertEqual(p.returncode, 2)


# ---- conteo de pruebas ---------------------------------------------------------------------------
class ConteoDePruebas(unittest.TestCase):
    def test_reconoce_los_corredores_mas_comunes(self):
        for salida, esperado in (("Ran 13 tests in 3.16s", 13), ("Ran 1 test in 0.00s", 1),
                                 ("13 passed, 1 skipped in 2.1s", 13), ("Tests:  7 passed, 7 total", 7),
                                 ("5 passing (20ms)", 5), ("# pass 9", 9)):
            self.assertEqual(co.contar_pruebas(salida), esperado, salida)

    def test_no_inventa_un_numero_cuando_no_hay_ninguno(self):
        for salida in ("no tests ran in 0.01s", "", "todo listo", "Ran tests"):
            self.assertIsNone(co.contar_pruebas(salida), salida)

    def test_cero_pruebas_se_distingue_de_no_poder_contarlas(self):
        self.assertEqual(co.contar_pruebas("Ran 0 tests in 0.000s"), 0)


if __name__ == "__main__":
    unittest.main()
