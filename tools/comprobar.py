"""Comprueba el proyecto con una sola definición de comandos: comprobaciones.json.

No instala dependencias, no aplica parches, no modifica el plan ni cierra tareas.
Solo ejecuta las comprobaciones declaradas y dice la verdad sobre lo que corrió:
un paso que termina sin error pero no pudo probar nada se reporta como FALLO, no
como éxito. Esa es la diferencia entre «el comando salió bien» y «se probó algo».

Correr desde la raíz del repo:
    python tools/comprobar.py rapido      # durante los cambios
    python tools/comprobar.py entrega     # antes de entregar o cerrar
    python tools/comprobar.py --listar    # qué configuración lee y qué haría cada perfil
    python tools/comprobar.py --ejemplo   # imprime un comprobaciones.json inicial

Códigos de salida: 0 todo bien · 1 alguna comprobación falló · 2 problema de uso o entorno.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

REL_CONFIG = "comprobaciones.json"
REL_LOGS = ".comprobaciones"
REL_VALIDAR = "tools/validar.py"
REL_BACKLOG = "docs/plan/backlog.md"
REL_CI = ".github/workflows/ci.yml"
VERSION_CONFIG = 1

# Cuánto exige cada alcance de distribución (docs/COMO-TRABAJAR.md, etapa 5).
DISTRIBUCIONES = ("solo-yo", "mis-dispositivos", "otras-personas")

# Estados de un paso. Solo FALLO y TIMEOUT cuentan como fracaso.
OK, FALLO, TIMEOUT, OMITIDO, EXCEPCION = "OK", "FALLO", "TIMEOUT", "OMITIDO", "EXCEPCION"
FRACASOS = (FALLO, TIMEOUT)

PERFILES_POR_OMISION = {
    "rapido": ["plan", "pruebas"],
    "entrega": ["plan", "pruebas", "dependencias", "comandos", "version", "plataformas", "licencia"],
}

# Para contar pruebas ejecutadas en la salida de los corredores más comunes.
# Si ninguno coincide, el paso falla: no se declara verde lo que no se pudo contar.
CONTEOS = (
    r"Ran\s+(\d+)\s+tests?\b",          # unittest
    r"(\d+)\s+passed\b",                # pytest, jest, vitest
    r"(\d+)\s+passing\b",               # mocha
    r"#\s*pass\s+(\d+)",                # node --test
)

ARCHIVOS_LICENCIA = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCIA", "LICENCIA.md", "COPYING")

EJEMPLO = """{
  "version": 1,
  "distribucion": "solo-yo",
  "plataformas": ["ubuntu-24.04 · python-3.12"],
  "stacks": {
    "python": {
      "pruebas": ["python", "-m", "pytest", "tests", "-q"],
      "pruebas_una": ["python", "-m", "pytest", "{ruta}", "-q"],
      "dependencias": ["requirements.txt"],
      "fijadas": true
    }
  },
  "comandos": {
    "instalar": "python -m pip install -r requirements.txt",
    "arrancar": null
  },
  "excepciones": []
}
"""


class ErrorDeUso(Exception):
    """Problema de uso o de entorno: devuelve 2 y no ejecuta nada."""


# ---- configuración -------------------------------------------------------------------------------
def cargar_config(raiz: Path) -> dict:
    """Lee y valida comprobaciones.json. Cualquier problema impide ejecutar (salida 2)."""
    p = raiz / REL_CONFIG
    if not p.is_file():
        raise ErrorDeUso(
            f"No existe {REL_CONFIG} en {raiz}. Lo crea T-001 al decidir el stack: "
            "corre «python tools/comprobar.py --ejemplo» para partir de un ejemplo. "
            "No se inventan comandos.")
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ErrorDeUso(f"{REL_CONFIG} no se pudo leer como JSON: {e}")
    if not isinstance(cfg, dict):
        raise ErrorDeUso(f"{REL_CONFIG} debe contener un objeto JSON.")

    if cfg.get("version") != VERSION_CONFIG:
        raise ErrorDeUso(f"{REL_CONFIG}: «version» debe ser {VERSION_CONFIG} (hay {cfg.get('version')!r}).")

    dist = cfg.get("distribucion")
    if dist not in DISTRIBUCIONES:
        raise ErrorDeUso(f"{REL_CONFIG}: «distribucion» debe ser uno de {', '.join(DISTRIBUCIONES)} "
                         f"(hay {dist!r}). Lo declara el diseño; ver la etapa 5 de COMO-TRABAJAR.md.")

    stacks = cfg.get("stacks")
    if not isinstance(stacks, dict) or not stacks:
        raise ErrorDeUso(f"{REL_CONFIG}: «stacks» debe tener al menos un stack con su comando de pruebas.")
    for nombre, s in sorted(stacks.items()):
        if not isinstance(s, dict):
            raise ErrorDeUso(f"{REL_CONFIG}: el stack «{nombre}» debe ser un objeto.")
        cmd = s.get("pruebas")
        if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) and x for x in cmd):
            raise ErrorDeUso(f"{REL_CONFIG}: el stack «{nombre}» necesita «pruebas» como lista de palabras, "
                             'por ejemplo ["python", "-m", "pytest", "tests", "-q"].')
        if not isinstance(s.get("dependencias", []), list):
            raise ErrorDeUso(f"{REL_CONFIG}: «dependencias» del stack «{nombre}» debe ser una lista de archivos.")
        una = s.get("pruebas_una")
        if una is not None and (not isinstance(una, list) or not all(isinstance(x, str) and x for x in una)):
            raise ErrorDeUso(f"{REL_CONFIG}: «pruebas_una» del stack «{nombre}» debe ser una lista de palabras con "
                             '{ruta} donde va la ruta, por ejemplo ["python", "-m", "pytest", "{ruta}", "-q"].')

    perfiles = cfg.get("perfiles", PERFILES_POR_OMISION)
    if not isinstance(perfiles, dict) or not perfiles:
        raise ErrorDeUso(f"{REL_CONFIG}: «perfiles» debe ser un objeto con una lista de pasos por perfil.")
    for nombre, pasos in sorted(perfiles.items()):
        if not isinstance(pasos, list) or not all(isinstance(x, str) and x for x in pasos):
            raise ErrorDeUso(f"{REL_CONFIG}: el perfil «{nombre}» debe ser una lista de nombres de paso.")
    cfg["perfiles"] = perfiles

    for exc in cfg.get("excepciones", []):
        if not isinstance(exc, dict) or not exc.get("paso") or not exc.get("motivo"):
            raise ErrorDeUso(f"{REL_CONFIG}: cada excepción necesita «paso» y «motivo»; "
                             "añade «hasta» y «fecha» para que no se vuelva permanente.")
    return cfg


def excepcion_de(cfg: dict, paso: str) -> dict | None:
    for exc in cfg.get("excepciones", []):
        if exc["paso"] == paso:
            return exc
    return None


def pasos_del_perfil(cfg: dict, perfil: str) -> list[str]:
    """Expande el perfil: «pruebas» y «dependencias» se abren por stack."""
    perfiles = cfg.get("perfiles") or PERFILES_POR_OMISION
    if perfil not in perfiles:
        raise ErrorDeUso(f"El perfil «{perfil}» no está en {REL_CONFIG}. "
                         f"Hay: {', '.join(sorted(perfiles))}.")
    pasos: list[str] = []
    for paso in perfiles[perfil]:
        if paso in ("pruebas", "dependencias"):
            pasos.extend(f"{paso}:{n}" for n in sorted(cfg["stacks"]))
        else:
            pasos.append(paso)
    return pasos


# ---- ejecución de comandos ------------------------------------------------------------------------
class Contexto:
    def __init__(self, raiz: Path, cfg: dict, python: str, logs: Path, timeout: int, ruta: str = ""):
        self.raiz, self.cfg, self.python, self.logs, self.timeout = raiz, cfg, python, logs, timeout
        self.ruta = ruta
        self.entorno = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
                            PYTHONDONTWRITEBYTECODE="1")

    def tokens(self, cmd: list[str]) -> list[str]:
        """Usa el intérprete de esta ejecución en vez del «python» del PATH."""
        if cmd and cmd[0] in ("python", "python3", "py"):
            return [self.python, *cmd[1:]]
        return list(cmd)

    def correr(self, paso: str, cmd: list[str]) -> tuple[int, str, float]:
        cmd = self.tokens(cmd)
        inicio = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=str(self.raiz), env=self.entorno, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace",
                                  timeout=self.timeout, check=False)
            codigo, salida = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
        except subprocess.TimeoutExpired:
            codigo, salida = 124, f"TIMEOUT: el paso superó {self.timeout} s."
        except OSError as e:
            codigo, salida = 127, f"No se pudo ejecutar {cmd[0]!r}: {e}"
        segundos = round(time.monotonic() - inicio, 2)
        self.guardar_log(paso, cmd, codigo, segundos, salida)
        return codigo, salida, segundos

    def guardar_log(self, paso: str, cmd: list[str], codigo: int, segundos: float, salida: str):
        self.logs.mkdir(parents=True, exist_ok=True)
        cabecera = (f"# paso: {paso}\n# comando: {' '.join(cmd)}\n"
                    f"# codigo: {codigo}\n# segundos: {segundos}\n\n")
        destino = self.logs / (paso.replace(":", "-") + ".log")
        with open(destino, "wb") as fh:          # binario: sin traducción de saltos de línea
            fh.write((cabecera + salida).encode("utf-8", "replace"))

    def modulo_existe(self, modulo: str) -> bool:
        """¿Se puede localizar el módulo desde la raíz del repo? No lo importa ni lo ejecuta."""
        codigo = ("import importlib.util as u, sys; "
                  "sys.exit(0 if u.find_spec(sys.argv[1]) else 1)")
        try:
            proc = subprocess.run([self.python, "-B", "-c", codigo, modulo], cwd=str(self.raiz),
                                  env=self.entorno, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=60, check=False)
        except (subprocess.TimeoutExpired, OSError):
            return False
        return proc.returncode == 0


def resultado(paso: str, estado: str, detalle: str, segundos: float = 0.0) -> dict:
    return {"paso": paso, "estado": estado, "detalle": detalle, "segundos": segundos}


def contar_pruebas(salida: str) -> int | None:
    for patron in CONTEOS:
        m = re.search(patron, salida)
        if m:
            return int(m.group(1))
    return None


# ---- pasos ----------------------------------------------------------------------------------------
def paso_plan(ctx: Contexto, _nombre: str) -> dict:
    if not (ctx.raiz / REL_VALIDAR).is_file():
        return resultado("plan", OMITIDO, f"todavía no existe {REL_VALIDAR}")
    if not (ctx.raiz / REL_BACKLOG).is_file():
        return resultado("plan", OMITIDO, f"todavía no hay {REL_BACKLOG}: el plan no se ha repartido")
    codigo, salida, seg = ctx.correr("plan", ["python", "-B", REL_VALIDAR, "--estricto"])
    if codigo != 0:
        return resultado("plan", FALLO, primera_linea_util(salida) or f"validar.py devolvió {codigo}", seg)
    return resultado("plan", OK, "diseño, plan, cobertura y tarjetas coherentes", seg)


def paso_pruebas(ctx: Contexto, nombre: str) -> dict:
    paso = f"pruebas:{nombre}"
    stack = ctx.cfg["stacks"][nombre]
    exc = excepcion_de(ctx.cfg, paso)

    cmd, nota = stack["pruebas"], ""
    if ctx.ruta:
        if stack.get("pruebas_una"):
            cmd = [t.replace("{ruta}", ctx.ruta) for t in stack["pruebas_una"]]
        else:
            nota = f" (el stack no declara «pruebas_una»: corrí la suite completa, no solo {ctx.ruta})"
    codigo, salida, seg = ctx.correr(paso, cmd)
    cuenta = contar_pruebas(salida)

    if codigo == 0 and cuenta:
        return resultado(paso, OK, f"{cuenta} pruebas ejecutadas{nota}", seg)

    if codigo == 124:
        motivo = f"superó {ctx.timeout} s"
        estado = TIMEOUT
    elif codigo != 0:
        motivo = primera_linea_util(salida) or f"el comando devolvió {codigo}"
        estado = FALLO
    elif cuenta == 0:
        motivo = "el comando terminó bien pero ejecutó 0 pruebas"
        estado = FALLO
    else:
        motivo = ("el comando terminó bien pero no pude contar pruebas ejecutadas: "
                  "un verde sin pruebas no demuestra nada. Revisa que el comando "
                  "ejecute pruebas de verdad, o declara una excepción con motivo y fecha")
        estado = FALLO

    if exc:
        hasta = f", hasta {exc['hasta']}" if exc.get("hasta") else ""
        fecha = f", declarada {exc['fecha']}" if exc.get("fecha") else ""
        return resultado(paso, EXCEPCION, f"{motivo}. Excepción: {exc['motivo']}{hasta}{fecha}", seg)
    return resultado(paso, estado, motivo, seg)


def paso_dependencias(ctx: Contexto, nombre: str) -> dict:
    paso = f"dependencias:{nombre}"
    stack = ctx.cfg["stacks"][nombre]
    archivos = stack.get("dependencias", [])
    if not archivos:
        return resultado(paso, OMITIDO, "el stack no declara archivos de dependencias")

    problemas: list[str] = []
    for rel in archivos:
        p = ctx.raiz / rel
        if not p.is_file():
            problemas.append(f"falta {rel}")
            continue
        if stack.get("fijadas") and rel.endswith(".txt"):
            sueltas = sin_fijar(p.read_text(encoding="utf-8"))
            if sueltas:
                problemas.append(f"{rel}: {len(sueltas)} sin fijar ({', '.join(sueltas[:3])})")
    if problemas:
        return resultado(paso, FALLO, "; ".join(problemas))
    return resultado(paso, OK, f"{len(archivos)} archivo(s) presentes y fijados: {', '.join(archivos)}")


def sin_fijar(texto: str) -> list[str]:
    """Líneas de un requirements que no fijan versión exacta. Una instalación reproducible las necesita."""
    sueltas = []
    for linea in texto.splitlines():
        l = linea.split("#", 1)[0].strip()
        if not l or l.startswith("-") or "@" in l:      # vacío, opción (-r, --hash) o URL directa
            continue
        if "==" not in l:
            sueltas.append(l)
    return sueltas


def paso_comandos(ctx: Contexto, _nombre: str) -> dict:
    comandos = {k: v for k, v in (ctx.cfg.get("comandos") or {}).items() if v}
    if not comandos:
        return resultado("comandos", OMITIDO, "no hay comandos declarados")

    problemas: list[str] = []
    revisados = 0
    for nombre, crudo in sorted(comandos.items()):
        if str(crudo).strip().lower() in ("(pendiente)", "pendiente"):
            problemas.append(f"{nombre}: sigue «(pendiente)»; lo concreta T-001")
            continue
        try:
            partes = shlex.split(str(crudo))
        except ValueError as e:
            problemas.append(f"{nombre}: no se pudo leer el comando ({e})")
            continue
        if not partes:
            continue
        revisados += 1
        programa = partes[0]
        if programa in ("python", "python3", "py"):
            pass                                        # es el intérprete de esta ejecución
        elif shutil.which(programa) is None and not (ctx.raiz / programa).exists():
            problemas.append(f"{nombre}: no existe el programa «{programa}»")
            continue
        for modulo in modulos_citados(partes):
            if not ctx.modulo_existe(modulo):
                problemas.append(f"{nombre}: no se encuentra el módulo «{modulo}»")
    if problemas:
        return resultado("comandos", FALLO, "; ".join(problemas))
    return resultado("comandos", OK, f"{revisados} comando(s) documentados existen y se pueden localizar")


def modulos_citados(partes: list[str]) -> list[str]:
    """Módulos que un comando nombra: «-m paquete» y «paquete.modulo:objeto»."""
    modulos = []
    for i, parte in enumerate(partes):
        if parte == "-m" and i + 1 < len(partes):
            modulos.append(partes[i + 1])
        elif re.fullmatch(r"[A-Za-z_][\w.]*:[A-Za-z_][\w.]*", parte):
            modulos.append(parte.split(":", 1)[0])
    return modulos


def paso_version(ctx: Contexto, _nombre: str) -> dict:
    if ctx.cfg["distribucion"] == "solo-yo":
        return resultado("version", OMITIDO, "distribución «solo-yo»: solo existe una copia, la tuya")
    encontradas = {}
    py = ctx.raiz / "pyproject.toml"
    if py.is_file():
        m = re.search(r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']', py.read_text(encoding="utf-8"))
        if m:
            encontradas["pyproject.toml"] = m.group(1)
    pkg = ctx.raiz / "package.json"
    if pkg.is_file():
        try:
            datos = json.loads(pkg.read_text(encoding="utf-8"))
            if isinstance(datos, dict) and datos.get("version"):
                encontradas["package.json"] = str(datos["version"])
        except ValueError:
            return resultado("version", FALLO, "package.json no se pudo leer como JSON")

    if not encontradas:
        return resultado("version", FALLO, "ningún manifiesto declara la versión del producto: "
                                           "sin versión no se puede decir en cuál aparece un fallo")
    distintas = set(encontradas.values())
    if len(distintas) > 1:
        detalle = ", ".join(f"{k} dice {v}" for k, v in sorted(encontradas.items()))
        return resultado("version", FALLO, f"los manifiestos no coinciden: {detalle}")
    return resultado("version", OK, f"versión {distintas.pop()} en {', '.join(sorted(encontradas))}")


def paso_plataformas(ctx: Contexto, _nombre: str) -> dict:
    if ctx.cfg["distribucion"] == "solo-yo":
        return resultado("plataformas", OMITIDO, "distribución «solo-yo»: basta tu propia máquina")
    declaradas = ctx.cfg.get("plataformas") or []
    if not declaradas:
        return resultado("plataformas", FALLO, "no declaraste plataformas y el software se instala en otra parte")
    ci = ctx.raiz / REL_CI
    if not ci.is_file():
        return resultado("plataformas", FALLO, f"no existe {REL_CI}: nadie comprueba las plataformas declaradas")
    texto = ci.read_text(encoding="utf-8")
    faltan = [p for p in declaradas if not all(t in texto for t in trozos(p))]
    if faltan:
        return resultado("plataformas", FALLO,
                         f"declaradas pero ausentes del CI: {', '.join(faltan)}. "
                         "Una plataforma sin ejecución es una promesa, no una comprobación")
    return resultado("plataformas", OK, f"{len(declaradas)} plataforma(s) declaradas aparecen en el CI")


def trozos(plataforma: str) -> list[str]:
    """Partes significativas de «ubuntu-24.04 · python-3.12» para buscarlas en el workflow."""
    return [t for t in re.split(r"[·/,\s]+", plataforma) if len(t) > 2]


def paso_licencia(ctx: Contexto, _nombre: str) -> dict:
    if ctx.cfg["distribucion"] != "otras-personas":
        return resultado("licencia", OMITIDO, f"distribución «{ctx.cfg['distribucion']}»: no se distribuye a terceros")
    for nombre in ARCHIVOS_LICENCIA:
        if (ctx.raiz / nombre).is_file():
            return resultado("licencia", OK, f"{nombre} presente")
    return resultado("licencia", FALLO, "no hay archivo de licencia y el software se distribuye a otras personas")


def paso_herramientas(ctx: Contexto, _nombre: str) -> dict:
    if not (ctx.raiz / "tools/tests").is_dir():
        return resultado("herramientas", OMITIDO, "no hay tools/tests en este repo")
    codigo, salida, seg = ctx.correr("herramientas", ["python", "-B", "-m", "unittest", "discover",
                                                      "-s", "tools/tests"])
    cuenta = contar_pruebas(salida)
    if codigo != 0:
        estado = TIMEOUT if codigo == 124 else FALLO
        return resultado("herramientas", estado, primera_linea_util(salida) or f"devolvió {codigo}", seg)
    return resultado("herramientas", OK, f"{cuenta or 0} pruebas de herramientas", seg)


PASOS = {
    "plan": paso_plan,
    "pruebas": paso_pruebas,
    "dependencias": paso_dependencias,
    "comandos": paso_comandos,
    "version": paso_version,
    "plataformas": paso_plataformas,
    "licencia": paso_licencia,
    "herramientas": paso_herramientas,
}


def primera_linea_util(salida: str) -> str:
    """La última línea con contenido: en pytest y unittest es la que resume el fallo."""
    lineas = [l.strip() for l in salida.splitlines() if l.strip()]
    return lineas[-1][:200] if lineas else ""


# ---- línea de comandos ----------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Ejecuta las comprobaciones declaradas del proyecto.")
    ap.add_argument("perfil", nargs="?", help="perfil a ejecutar (por ejemplo rapido o entrega)")
    ap.add_argument("--repo", default=".", help="raíz del repositorio (por defecto, directorio actual)")
    ap.add_argument("--python", help="intérprete con el que correr los pasos (por defecto, este)")
    ap.add_argument("--ruta", default="", help="probar solo esta ruta (la que indica la tarjeta), si el stack "
                                               "declara «pruebas_una»")
    ap.add_argument("--timeout", type=int, default=900, help="límite en segundos por paso (por defecto 900)")
    ap.add_argument("--listar", action="store_true", help="muestra la configuración y los pasos de cada perfil")
    ap.add_argument("--ejemplo", action="store_true", help="imprime un comprobaciones.json inicial")
    args = ap.parse_args(argv)

    if args.ejemplo:
        print(EJEMPLO, end="")
        return 0

    raiz = Path(args.repo).resolve()
    try:
        cfg = cargar_config(raiz)
        if args.listar:
            return listar(cfg)
        if not args.perfil:
            ap.error("falta el perfil (por ejemplo «rapido» o «entrega»), o usa --listar")
        pasos = pasos_del_perfil(cfg, args.perfil)
    except ErrorDeUso as e:
        print(f"No se pudo comprobar: {e}")
        return 2

    python = args.python or sys.executable
    if args.python and not Path(args.python).is_file():
        print(f"No se pudo comprobar: {args.python} no es un intérprete existente.")
        return 2

    sello = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    ctx = Contexto(raiz, cfg, python, raiz / REL_LOGS / sello, args.timeout, args.ruta)

    alcance = f" · solo {args.ruta}" if args.ruta else ""
    print(f"Perfil «{args.perfil}» · distribución «{cfg['distribucion']}»{alcance} · {len(pasos)} pasos\n")
    resultados = []
    for paso in pasos:
        base, _, nombre = paso.partition(":")
        funcion = PASOS.get(base)
        if funcion is None:
            resultados.append(resultado(paso, FALLO, f"no existe el paso «{base}» "
                                                     f"(hay: {', '.join(sorted(PASOS))})"))
        elif nombre and nombre not in cfg["stacks"]:
            resultados.append(resultado(paso, FALLO, f"el stack «{nombre}» no está en {REL_CONFIG}"))
        else:
            resultados.append(funcion(ctx, nombre))
        r = resultados[-1]
        tiempo = f"{r['segundos']:>7.2f} s" if r["segundos"] else " " * 9
        print(f"  {r['paso']:<22} {r['estado']:<10}{tiempo}  {r['detalle']}")

    fallidos = [r for r in resultados if r["estado"] in FRACASOS]
    excepciones = [r for r in resultados if r["estado"] == EXCEPCION]
    total = round(sum(r["segundos"] for r in resultados), 2)
    print(f"\n{len(resultados)} pasos en {total} s. Logs completos en {REL_LOGS}/{sello}/")

    if excepciones:
        print(f"Excepciones vigentes ({len(excepciones)}): "
              f"{', '.join(r['paso'] for r in excepciones)}. Son deuda declarada, no verde.")
    if fallidos:
        print(f"Comprobación fallida: {len(fallidos)} de {len(resultados)} pasos "
              f"({', '.join(r['paso'] for r in fallidos)}).")
        return 1
    print("Comprobación superada: cada paso ejecutado probó algo.")
    return 0


def listar(cfg: dict) -> int:
    print(f"{REL_CONFIG}: versión {cfg['version']} · distribución «{cfg['distribucion']}»")
    print(f"Plataformas declaradas: {', '.join(cfg.get('plataformas') or ['(ninguna)'])}")
    for nombre, s in sorted(cfg["stacks"].items()):
        deps = ", ".join(s.get("dependencias", [])) or "(ninguna)"
        print(f"Stack «{nombre}»: pruebas = {' '.join(s['pruebas'])} · dependencias = {deps}"
              f"{' · fijadas' if s.get('fijadas') else ''}")
    for nombre, valor in sorted((cfg.get("comandos") or {}).items()):
        print(f"Comando «{nombre}»: {valor or '(sin declarar)'}")
    for perfil in sorted(cfg["perfiles"]):
        print(f"Perfil «{perfil}»: {', '.join(pasos_del_perfil(cfg, perfil))}")
    for exc in cfg.get("excepciones", []):
        print(f"Excepción en «{exc['paso']}»: {exc['motivo']}"
              f"{' (hasta ' + exc['hasta'] + ')' if exc.get('hasta') else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
