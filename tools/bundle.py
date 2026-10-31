#!/usr/bin/env python3
"""Arma el bundle de una tarea: un solo archivo con lo justo que un LLM necesita. Solo usa la biblioteca estándar.

Uso, desde la raíz del repo:
    python tools/bundle.py T-007                 arma bundles/T-007.md
    python tools/bundle.py T-007 --forzar        salta la compuerta de dependencias (bajo tu responsabilidad)
    python tools/bundle.py T-007 --parche2       modo estricto, parche 2: suma los tests del parche 1
    python tools/bundle.py T-007 --max-kb 80     cambia el tamaño desde el cual avisa (por defecto, 60)

El bundle trae, en este orden: el árbol del repo · el «Entorno del usuario» · la tarjeta · los documentos que la
tarjeta manda leer (siempre con docs/00-LEEME-IA.md primero) · el contenido actual de los archivos de «Tocar:»
que ya existen. Sin duplicar archivos. Los textos se normalizan a saltos de línea LF, como los guarda git.

Se niega a armarlo (no escribe nada) si:
    - un ADR de «Leer:» no está «aceptada» (no hay forma de saltarlo: aceptarlo es una decisión tuya);
    - una tarea de «Depende de:» no está hecha (--forzar lo salta). Una tarea está hecha cuando su tarjeta
      ya no existe en docs/plan/tareas/: así se borra al cerrarla;
    - un archivo de «Leer:» no existe y la tarjeta no dice qué tarea lo produce («lo produce T-003»);
    - la tarjeta no se puede leer (le falta «Estado:», «Leer:» o «Tocar:», o trae algo que no es una ruta).

El «Entorno del usuario» sale de ~/.metodo-ia.json (claves «terminal» y «carpeta_parches»); la carpeta del repo
es esta. Si el archivo falta, el bundle lo dice y el LLM pregunta una vez: no se inventa nada.

Códigos de salida:
    0  bundle armado (puede haber avisos)
    1  se negó: la tarjeta tiene errores o falla una compuerta
    2  problema de uso o del entorno (no existe la tarjeta, no hay git, no se pudo escribir)
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

import init_diseno as idz  # mismo lector de bloques y mismo formato de salida
import init_plan as ip     # para leer el backlog guardado

MAX_KB = 60  # provisional: se calibra con la primera app real
REL_TAREAS = "docs/plan/tareas"
REL_LEEME = "docs/00-LEEME-IA.md"
CLAVES_ENTORNO = ("terminal", "carpeta_parches")

RE_ID = re.compile(r"^(?:T|REF)-\d+$")
RE_TITULO = re.compile(r"^#\s+((?:T|REF)-\d+)\s+·\s+(.+)$")
RE_ESTADO = re.compile(r"^Estado:\s*(.*?)\s*$")
RE_MODO = re.compile(r"^Modo:\s*(.*?)\s*$")
RE_LEER = re.compile(r"^Leer(?:\s*\(solo esto\))?:\s*(.*?)\s*$")
RE_TOCAR = re.compile(r"^Tocar:\s*(.*?)\s*$")
RE_ITEM = re.compile(r"^(?P<ruta>[^\s(]+)(?:\s*\((?P<nota>.*)\))?$")
RE_PRODUCE = re.compile(r"lo produce\s+((?:T|REF)-\d+)")
RE_ADR = re.compile(r"^docs/decisiones/(\d{4})-.+\.md$")
RE_ESTADO_ADR = re.compile(r"^Estado:\s*([^·]*?)\s*(?:·|$)")

Item = namedtuple("Item", "ruta ancla nota produce")


class GitError(Exception):
    """git no está o no pudo contestar."""


# ---- la tarjeta ----------------------------------------------------------------------
class Tarjeta:
    """Lee de una tarjeta de docs/plan/tareas/ lo que el bundle necesita."""

    def __init__(self, texto):
        self.lineas = texto.splitlines()
        self.tipos = idz.clasificar(self.lineas)
        self.errores = []  # (línea, mensaje)
        self.avisos = []
        self.id = self.titulo = self.modo = None
        self.depende = None  # lista de IDs; None si no se pudo leer
        self.leer = []
        self.tocar = []
        self._leer_campos()

    def _items(self, n, valor, campo):
        salida = []
        for crudo in valor.split(" · "):
            crudo = crudo.strip()
            if not crudo:
                continue
            if "«" in crudo or "»" in crudo:
                self.avisos.append((n, f"«{campo}» trae un campo de la plantilla sin llenar: {crudo[:50]}"))
                continue
            m = RE_ITEM.match(crudo)
            if not m:
                self.errores.append((n, f"no entiendo «{crudo[:50]}» en «{campo}»: cada elemento es una ruta, "
                                        "con una nota entre paréntesis si hace falta"))
                continue
            ruta, _, ancla = m.group("ruta").partition("#")
            nota = (m.group("nota") or "").strip()
            produce = RE_PRODUCE.search(nota)
            salida.append(Item(ruta, ancla, nota, produce.group(1) if produce else None))
        return salida

    def _leer_campos(self):
        vistos = {}
        sin_llenar = None
        for i, linea in enumerate(self.lineas):
            if self.tipos[i] != "t":
                continue
            n = i + 1
            if sin_llenar is None and ("«" in linea or "»" in linea):
                sin_llenar = n
            m = RE_TITULO.match(linea.strip())
            if m and self.id is None:
                self.id, self.titulo = m.group(1), m.group(2).strip()
                continue
            for clave, regex in (("estado", RE_ESTADO), ("modo", RE_MODO), ("leer", RE_LEER), ("tocar", RE_TOCAR)):
                m = regex.match(linea)
                if m and clave not in vistos:
                    vistos[clave] = (n, m.group(1))
        if sin_llenar is not None:
            self.avisos.append((sin_llenar, "la tarjeta tiene campos de la plantilla sin llenar"))
        if self.id is None:
            self.errores.append((1, "la tarjeta debe empezar con «# T-001 · Título»"))
        self._estado(vistos.get("estado"))
        if "modo" in vistos:
            n, valor = vistos["modo"]
            if valor and "«" not in valor and valor != "estricto":
                self.errores.append((n, f"«Modo:» solo puede valer «estricto» (encontré «{valor}»)"))
            elif valor == "estricto":
                self.modo = "estricto"
        for clave, campo, destino in (("leer", "Leer (solo esto):", "leer"), ("tocar", "Tocar:", "tocar")):
            if clave not in vistos:
                self.errores.append((0, f"falta la línea «{campo} …» en la tarjeta"))
            else:
                n, valor = vistos[clave]
                setattr(self, destino, self._items(n, valor, campo))

    def _estado(self, dato):
        if dato is None:
            self.errores.append((0, "falta la línea «Estado: … · Depende de: … · Cubre: …» en la tarjeta"))
            return
        n, valor = dato
        dep = None
        for parte in valor.split(" · "):
            parte = parte.strip()
            if parte.startswith("Depende de:"):
                dep = parte[len("Depende de:"):].strip()
        if dep is None:
            self.errores.append((n, "la línea «Estado:» no trae «Depende de: …»"))
        elif "«" in dep or "»" in dep:
            self.avisos.append((n, "«Depende de:» sin llenar: no pude comprobar las dependencias"))
            self.depende = []
        elif dep in ip.VACIOS:
            self.depende = []
        else:
            tokens = ip._partir(dep)
            malos = [t for t in tokens if not RE_ID.match(t)]
            if malos or not tokens:
                self.errores.append((n, f"«Depende de:» cita «{malos[0] if malos else dep}», que no es una "
                                        "tarea (usa T-001, o — si no depende de ninguna)"))
            else:
                self.depende = tokens


# ---- git y archivos ------------------------------------------------------------------
def _git(raiz, *args):
    try:
        return subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(raiz), *args],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as e:
        raise GitError(f"no pude correr git ({e}). Instálalo y corre el comando desde la raíz del repo")


def listar_archivos(raiz):
    """Archivos del repo que existen hoy: los que git sigue y los nuevos que no ignora."""
    r = _git(raiz, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if r.returncode != 0:
        raise GitError("git no pudo listar los archivos (¿esta carpeta es un repo?): "
                       + (r.stderr.strip() or f"código {r.returncode}"))
    return {p for p in r.stdout.split("\0") if p and (raiz / p).is_file()}


def expandir(archivos, ruta):
    """Archivos que cubre una ruta de la tarjeta: el archivo exacto, o los que cuelgan de una carpeta o de un
    patrón con «*» (el «*» es recursivo, como dice la tarjeta)."""
    if "*" in ruta:
        return sorted(p for p in archivos if fnmatch.fnmatchcase(p, ruta))
    if ruta in archivos:
        return [ruta]
    prefijo = ruta.rstrip("/") + "/"
    return sorted(p for p in archivos if p.startswith(prefijo))


def leer_archivo(raiz, ruta):
    """(texto con saltos LF, None) o (None, motivo por el que se omite)."""
    try:
        crudo = (raiz / ruta).read_bytes()
    except OSError as e:
        return None, f"no se pudo leer ({e})"
    if b"\0" in crudo:
        return None, "es un archivo binario"
    try:
        return crudo.decode("utf-8-sig").replace("\r\n", "\n"), None
    except UnicodeDecodeError:
        return None, "no está en UTF-8"


def estado_adr(raiz, ruta):
    """El «Estado:» de un ADR en minúsculas, o None si no se encuentra."""
    texto, _ = leer_archivo(raiz, ruta)
    if texto is None:
        return None
    lineas = texto.splitlines()
    tipos = idz.clasificar(lineas)
    for i, linea in enumerate(lineas):
        if tipos[i] == "t":
            m = RE_ESTADO_ADR.match(linea)
            if m:
                return m.group(1).strip().lower()
    return None


def leer_entorno(home):
    """(datos, aviso): lo que dice ~/.metodo-ia.json. Sin inventar nada: lo que falta, falta."""
    datos, aviso = {}, None
    try:
        ruta = (home if home is not None else Path.home()) / ".metodo-ia.json"
    except RuntimeError:
        return datos, "no pude ubicar tu carpeta personal para leer ~/.metodo-ia.json"
    if ruta.is_file():
        try:
            crudo = json.loads(ruta.read_bytes().decode("utf-8-sig"))  # utf-8-sig: PowerShell suele guardar con BOM
            if not isinstance(crudo, dict):
                raise ValueError("no es un objeto JSON")
            for clave in CLAVES_ENTORNO:
                valor = crudo.get(clave)
                if isinstance(valor, str) and valor.strip():
                    datos[clave] = valor.strip()
        except (ValueError, UnicodeDecodeError) as e:
            aviso = f"no pude leer {ruta} ({e}); lo trato como sin configurar"
    faltan = [c for c in CLAVES_ENTORNO if c not in datos]
    if faltan and aviso is None:
        aviso = ("~/.metodo-ia.json no existe o no trae " + " ni ".join(f"«{c}»" for c in faltan)
                 + ": el LLM te preguntará esos datos una vez")
    return datos, aviso


# ---- armado del texto ----------------------------------------------------------------
def _valla(contenido):
    """Cuatro acentos graves, o más si el contenido ya trae vallas largas."""
    corridas = [len(c) for c in re.findall(r"`+", contenido)]
    return "`" * max(4, max(corridas + [0]) + 1)


def _bloque(contenido):
    valla = _valla(contenido)
    cuerpo = contenido if (contenido == "" or contenido.endswith("\n")) else contenido + "\n"
    return f"{valla}\n{cuerpo}{valla}\n"


def _kb(n_bytes):
    return f"{n_bytes / 1024:.1f} KB"


def _tokens(texto):
    n = len(texto) // 4
    n = int(round(n, -2)) if n >= 1000 else n
    return f"{n:,}".replace(",", ".")


class Resultado:
    def __init__(self):
        self.codigo = 0
        self.tarea = None
        self.titulo = None
        self.rel_tarjeta = None
        self.errores = []     # (línea, mensaje) de la tarjeta
        self.negativas = []   # por qué se niega (compuertas y archivos que faltan)
        self.avisos = []
        self.notas = []       # informativas (qué dependencias estaban hechas...)
        self.incluidos = []   # (sección, ruta, bytes)
        self.por_crear = []
        self.arbol = 0
        self.texto = None

    def parar(self, codigo, mensaje):
        self.codigo = codigo
        self.negativas.append(mensaje)
        return self


def armar(raiz, tarea, forzar=False, parche2=False, max_kb=MAX_KB, home=None):
    """Arma el bundle en memoria. No escribe nada: devuelve un Resultado (con .texto si salió bien)."""
    res = Resultado()
    tarea = (tarea or "").strip().upper()
    res.tarea = tarea
    if not RE_ID.match(tarea):
        return res.parar(2, f"«{tarea}» no es el número de una tarea (usa T-007 o REF-01)")
    res.rel_tarjeta = f"{REL_TAREAS}/{tarea}.md"
    ruta_t = raiz / res.rel_tarjeta
    if not ruta_t.is_file():
        return res.parar(2, f"no existe la tarjeta {res.rel_tarjeta}. O la tarea ya está hecha (su tarjeta se "
                            "borra al cerrarla) o su ola todavía no se repartió con init_plan.py")
    try:
        texto_t = ruta_t.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeDecodeError:
        return res.parar(1, f"{res.rel_tarjeta} no está en UTF-8")
    t = Tarjeta(texto_t)
    if t.id is not None and t.id != tarea:
        t.errores.append((1, f"el título dice {t.id}, pero el archivo es {tarea}.md"))
    res.titulo = t.titulo
    res.avisos += [f"{res.rel_tarjeta}:{n}: {m}" for n, m in t.avisos]
    if t.errores:
        res.errores = sorted(t.errores)
        res.codigo = 1
        return res
    if parche2 and t.modo != "estricto":
        return res.parar(1, "--parche2 solo sirve con una tarjeta de «Modo: estricto»; esta no lo es")
    try:
        archivos = listar_archivos(raiz)
    except GitError as e:
        return res.parar(2, str(e))

    hecha = lambda tid: not (raiz / REL_TAREAS / f"{tid}.md").exists()  # noqa: E731

    # --- compuerta de dependencias
    backlog = None
    if t.depende:
        ruta_b = raiz / ip.REL_BACKLOG
        if ruta_b.is_file():
            try:
                backlog = ip.leer_backlog_guardado(ruta_b.read_bytes().decode("utf-8-sig"))
            except (ValueError, UnicodeDecodeError) as e:
                res.avisos.append(f"no pude leer {ip.REL_BACKLOG} ({e}); no comprobé que las dependencias existan")
        else:
            res.avisos.append(f"no encontré {ip.REL_BACKLOG}; no comprobé que las dependencias existan")
    pendientes = []
    for d in t.depende or []:
        if backlog is not None and d.startswith("T-") and d not in backlog.tareas:
            res.negativas.append(f"{d}, de «Depende de:», no está en {ip.REL_BACKLOG}: ¿un error de la tarjeta?")
        elif hecha(d):
            res.notas.append(f"{d} está hecha (su tarjeta ya no existe)")
        else:
            pendientes.append(d)
    forzadas = []
    if pendientes and forzar:
        forzadas = pendientes
        res.avisos.append("saltaste la compuerta de dependencias (--forzar): no está(n) hecha(s) "
                          + ", ".join(pendientes))
    else:
        for d in pendientes:
            res.negativas.append(f"{d} no está hecha: su tarjeta docs/plan/tareas/{d}.md todavía existe. Termínala "
                                 f"y bórrala (git rm) antes de seguir. --forzar salta esta compuerta, bajo tu responsabilidad")

    # --- documentos de «Leer:» (las reglas siempre primero)
    items = [Item(REL_LEEME, "", "", None)] + [i for i in t.leer if i.ruta != REL_LEEME]
    leer, vistos, por_crear = [], set(), []
    for it in items:
        encontrados = expandir(archivos, it.ruta)
        if not encontrados:
            if it.ruta == REL_LEEME:
                res.negativas.append(f"no existe {REL_LEEME}: es el archivo con las reglas y viaja en cada bundle")
            elif it.produce and hecha(it.produce):
                res.negativas.append(f"{it.ruta} (de «Leer:»): la tarjeta dice que lo produce {it.produce}, "
                                     "que ya está hecha, pero el archivo no existe")
            elif it.produce:
                por_crear.append(f"{it.ruta} (lo produce {it.produce})")
            else:
                res.negativas.append(f"{it.ruta} (de «Leer:») no existe y la tarjeta no dice qué tarea lo produce")
            continue
        for ruta in encontrados:
            if ruta not in vistos:
                vistos.add(ruta)
                leer.append((ruta, it.ancla))

    # --- compuerta de ADR
    for ruta, _ in leer:
        m = RE_ADR.match(ruta)
        if not m:
            continue
        estado, num = estado_adr(raiz, ruta), m.group(1)
        if estado == "aceptada":
            continue
        if estado is None:
            res.negativas.append(f"ADR-{num} ({ruta}): no encuentro su línea «Estado: …»")
        elif estado == "propuesta":
            res.negativas.append(f"ADR-{num} sigue en «propuesta». Solo tú la pasas a «aceptada» (cambia su línea "
                                 "«Estado:») y haces commit; después vuelve a armar el bundle")
        elif estado == "reemplazada":
            res.negativas.append(f"ADR-{num} está «reemplazada»: la tarjeta debe citar la decisión que la reemplaza")
        else:
            res.negativas.append(f"ADR-{num}: el estado «{estado}» no es válido (propuesta, aceptada o reemplazada)")

    # --- archivos de «Tocar:»
    tocar_todos, tocar_nuevos = [], []
    for it in t.tocar:
        encontrados = expandir(archivos, it.ruta)
        if not encontrados:
            tocar_nuevos.append(it.ruta)
        for ruta in encontrados:
            if ruta not in tocar_todos:
                tocar_todos.append(ruta)
    tests = [r for r in tocar_todos if r.startswith("tests/")]
    if parche2 and not tests:
        res.negativas.append("con --parche2 esperaba los tests del parche 1 entre los archivos de «Tocar:» "
                             "(carpeta tests/), y no hay ninguno. ¿Hiciste el commit del parche 1?")
    if t.modo == "estricto" and not parche2 and tests:
        res.avisos.append("la tarjeta es de modo estricto y ya hay tests en «Tocar:». Si es el parche 2, vuelve a "
                          "armar el bundle con --parche2; si es el parche 1, ignora este aviso")

    if res.negativas:
        res.codigo = 1
        return res

    # --- contenidos
    omitidos = []

    def cargar(seccion, rutas):
        salida = []
        for ruta in rutas:
            contenido, motivo = leer_archivo(raiz, ruta)
            if contenido is None:
                omitidos.append(f"{ruta} se omitió: {motivo}")
                continue
            salida.append((ruta, contenido))
            res.incluidos.append((seccion, ruta, len(contenido.encode("utf-8"))))
        return salida

    anclas = {r: a for r, a in leer if a}
    leer_c = cargar("leer", [r for r, _ in leer])
    tests_nuevos = [r for r in tests if r not in vistos] if parche2 else []
    tests_c = cargar("tests", tests_nuevos)
    en_otro = vistos | (set(tests) if parche2 else set())
    tocar_c = cargar("tocar", [r for r in tocar_todos if r not in en_otro])
    res.avisos += omitidos
    res.por_crear = por_crear + tocar_nuevos

    # --- entorno y árbol
    entorno, aviso_entorno = leer_entorno(home)
    if aviso_entorno:
        res.avisos.append(aviso_entorno)
    arbol = sorted(archivos)
    res.arbol = len(arbol)
    r = _git(raiz, "status", "--porcelain")
    if r.returncode == 0 and r.stdout.strip():
        res.avisos.append(f"hay {len(r.stdout.splitlines())} archivo(s) con cambios sin guardar: el bundle muestra "
                          "lo que hay en tu disco, no el último commit")
    r = _git(raiz, "check-ignore", "-q", "bundles/x.md")
    if r.returncode == 1:
        res.avisos.append("bundles/ no está en .gitignore: un «git add -A» guardaría los bundles. Agrega la línea "
                          "«bundles/» a .gitignore")

    # --- el texto
    p = [f"# Bundle de {t.id} · {t.titulo}\n",
         "Armado por `tools/bundle.py`. Trae, en este orden: el árbol del repo · el «Entorno del usuario» · la "
         "tarjeta · los documentos que la tarjeta manda leer · el contenido actual de los archivos de `Tocar:` que "
         "ya existen. Empieza por las reglas de `docs/00-LEEME-IA.md` (van más abajo).\n"]
    if parche2:
        p.append("**Modo estricto, parche 2.** Implementa la tarea. Los tests del parche 1 ya están en el repo: van "
                 "más abajo, y valen como `Leer:` y como `No tocar:` (no los modifiques).\n")
    if forzadas:
        p.append(f"**Dependencias no hechas** (se saltó la compuerta con --forzar): {', '.join(forzadas)}. "
                 "Puede que sus archivos todavía no existan: usa solo lo que está en el árbol.\n")
    p.append("## Árbol del repo\n\n" + _bloque("\n".join(arbol)))
    carpetas = {"terminal": "Terminal", "carpeta_parches": "Carpeta de parches"}
    lineas_env = [f"- {carpetas[c]}: {entorno.get(c, '(sin configurar)')}" for c in CLAVES_ENTORNO]
    lineas_env.append(f"- Carpeta del repo: {raiz}")
    p.append("## Entorno del usuario\n\n" + "\n".join(lineas_env) + "\n")
    p.append(f"## Tarjeta {t.id}\n\n" + _bloque(texto_t))
    p.append("## Documentos que la tarjeta manda leer\n")
    for ruta, contenido in leer_c:
        nota = f"La tarjeta pide la parte «#{anclas[ruta]}»; va el archivo completo.\n\n" if ruta in anclas else ""
        p.append(f"### {ruta}\n\n{nota}{_bloque(contenido)}")
    if por_crear:
        p.append("Todavía no existen (los producen tareas previas): " + "; ".join(por_crear) + "\n")
    if parche2:
        p.append("### Tests del parche 1 (también en `No tocar:`)\n")
        p.append("Ya existen en el repo. Léelos; no los modifiques.\n" if tests_c else
                 "Los tests del parche 1 ya van arriba, entre los documentos de `Leer:`.\n")
        for ruta, contenido in tests_c:
            p.append(f"### {ruta}\n\n{_bloque(contenido)}")
    p.append("## Archivos de `Tocar:` que ya existen\n")
    if not tocar_c:
        p.append("Ninguno todavía: la tarea los crea.\n")
    for ruta, contenido in tocar_c:
        p.append(f"### {ruta}\n\n{_bloque(contenido)}")
    if tocar_nuevos:
        p.append("Por crear (no existen todavía): " + "; ".join(tocar_nuevos) + "\n")
    res.texto = "\n".join(p)

    if len(res.texto.encode("utf-8")) > max_kb * 1024:
        res.avisos.append(f"el bundle pesa {_kb(len(res.texto.encode('utf-8')))} y el límite es {max_kb} KB: "
                          "una tarea tan grande conviene partirla (o sube el límite con --max-kb)")
    return res


# ---- línea de comandos -------------------------------------------------------------------
def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):  # que una consola con otra codificación no tumbe el programa
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="bundle.py",
                                 description="Arma el bundle de una tarea: un solo archivo con lo justo para el LLM.")
    ap.add_argument("tarea", help="número de la tarea, por ejemplo T-007 (o REF-01)")
    ap.add_argument("--forzar", action="store_true",
                    help="salta la compuerta de dependencias (bajo tu responsabilidad); no salta la de los ADR")
    ap.add_argument("--parche2", action="store_true",
                    help="modo estricto, parche 2: suma los tests del parche 1 (que valen como Leer y No tocar)")
    ap.add_argument("--max-kb", type=int, default=MAX_KB, metavar="N",
                    help=f"tamaño desde el cual avisa que conviene partir la tarea (por defecto, {MAX_KB})")
    args = ap.parse_args(argv)
    if args.max_kb < 1:
        ap.error("--max-kb debe ser un número positivo")

    raiz = Path(__file__).resolve().parent.parent
    res = armar(raiz, args.tarea, args.forzar, args.parche2, args.max_kb)
    if res.errores:
        idz._mostrar("Errores", res.errores, res.rel_tarjeta)
    if res.negativas or res.errores:
        print(f"\nNo se armó el bundle de {res.tarea}. Motivos:")
        for m in res.negativas:
            print(f"  - {m}")
        if res.errores:
            print(f"  - La tarjeta tiene {len(res.errores)} error(es): corrígela y vuelve a correr el comando.")
        elif res.codigo == 1:
            print("Resuelve lo anterior y vuelve a correr el comando.")
        if res.avisos:
            print("\nAvisos:")
            for a in res.avisos:
                print(f"  - {a}")
        return res.codigo

    salida = raiz / "bundles" / f"{res.tarea}.md"
    try:
        salida.parent.mkdir(exist_ok=True)
        with open(salida, "w", encoding="utf-8", newline="\n") as f:
            f.write(res.texto)
    except OSError as e:
        print(f"No pude escribir {salida} ({e}).")
        return 2

    print(f"Bundle de {res.tarea} · {res.titulo}: bundles/{res.tarea}.md  "
          f"({_kb(len(res.texto.encode('utf-8')))}, unos {_tokens(res.texto)} tokens)")
    print(f"\nIncluye: el árbol ({idz._cuenta(res.arbol, 'archivo', 'archivos')}), el entorno, la tarjeta y:")
    for seccion, titulo in (("leer", "Leer"), ("tests", "Tests del parche 1"), ("tocar", "Tocar (ya existen)")):
        filas = [(r, n) for s, r, n in res.incluidos if s == seccion]
        if filas:
            print(f"  {titulo}: {idz._cuenta(len(filas), 'archivo', 'archivos')}, {_kb(sum(n for _, n in filas))}")
            for r, n in filas:
                print(f"    {r}  ({_kb(n)})")
    if res.por_crear:
        print(f"  Por crear: {'; '.join(res.por_crear)}")
    for n in res.notas:
        print(f"Dependencias: {n}.")
    if res.avisos:
        print(f"\nAvisos ({len(res.avisos)}):")
        for a in res.avisos:
            print(f"  - {a}")
    print(f"\nSiguiente paso: abre bundles/{res.tarea}.md, copia todo su contenido y pégalo en el LLM, "
          "debajo del texto de «Tarea» de docs/COMO-TRABAJAR.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
