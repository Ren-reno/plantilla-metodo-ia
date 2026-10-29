#!/usr/bin/env python3
"""Reparte PLAN.md en docs/plan/ y revisa su formato. Solo usa la biblioteca estándar.

Uso, desde la raíz del repo:
    python tools/init_plan.py PLAN.md            revisa el formato y reparte el plan en docs/plan/
    python tools/init_plan.py PLAN.md --check    solo revisa: no escribe nada y muestra qué repartiría
    python tools/init_plan.py PLAN.md --force    acepta un plan completo aunque ya haya un backlog guardado

Reconoce tres situaciones, por los títulos «##» del archivo y por lo que ya hay en docs/plan/:
    primera vez       «## Backlog», «## Matriz de cobertura» y «## Tarjetas de la ola 1»; aún no hay backlog guardado
    olas siguientes   solo «## Tarjetas de la ola N»; las tarjetas se verifican contra docs/plan/backlog.md
    replanificación   las tres secciones con un backlog ya guardado: versión = la guardada + 1 y «Motivo del cambio:»

Qué va a dónde:
    «## Backlog»                     -> docs/plan/backlog.md    (con el título y la línea de versión)
    «## Matriz de cobertura»         -> docs/plan/cobertura.md  (ídem; se copia tal cual, no se recalcula)
    cada «### T-xxx» o «### REF-xx»  -> docs/plan/tareas/T-xxx.md (las tarjetas que ya existen no se pisan nunca)
    el original                      -> docs/archivo/ con su propio nombre (si estaba en la raíz del repo, se mueve)

Esta herramienta comprueba que el plan está bien escrito y que sus referencias internas existen. Que el plan
tenga sentido (ciclos, cobertura real contra los requisitos, matriz escrita = calculada) lo revisará validar.py.

Códigos de salida:
    0  todo bien (puede haber avisos)
    1  el formato tiene errores: no se escribió nada
    2  problema de uso, del repo o de escritura (no hay backlog guardado, el plan ya está repartido...)
"""
from __future__ import annotations

import argparse
import difflib
import re
import shutil
import sys
from pathlib import Path

import init_diseno as idz  # mismo analizador de bloques y mismo formato de salida que init_diseno.py

# Títulos "##" exactos (los scripts dependen de ellos).
BACKLOG = "Backlog"
MATRIZ = "Matriz de cobertura"
TARJETAS = "Tarjetas de la ola N"
TARJETAS_CLAVE = "tarjetas"
VACIOS = ("—", "–", "-")  # «no depende de nada» / «no cubre nada»
REL_BACKLOG = "docs/plan/backlog.md"
REL_COBERTURA = "docs/plan/cobertura.md"

RE_H1 = re.compile(r"^PLAN\s*[—–-]\s*(.+)$")
RE_VERSION = re.compile(r"^>\s*Versi[oó]n\s+«?\s*(\d+)\s*»?")
RE_MOTIVO = re.compile(r"^>\s*Motivo del cambio:\s*(.*?)\s*$")
RE_OLA = re.compile(r"^Tarjetas de la ola\s+(\d+)$")
RE_REBANADA = re.compile(r"^Rebanada\s+(\d+)\s+·\s+(.+)$")
RE_TAREA = re.compile(r"^-\s+(T-\d+)\s+·\s+(.+?)\s+·\s+Depende de:\s*(.*?)\s+·\s+Cubre:\s*(.*?)\s*$")
RE_TARJETA = re.compile(r"^((?:T|REF)-\d+)\s+·\s+(.+)$")
RE_ID_TAREA = re.compile(r"^T-\d+$")
RE_CUBRE = re.compile(r"^(?:[CR]\d+(?:\s*\([^)]*\))?|RF-\d+|RN-\d+|RNF-\d+)$")
RE_VINETA = re.compile(r"^-\s+\S")


# ---- utilidades de texto ----------------------------------------------------
def _limpio(texto):
    """Quita las marcas «» de un campo de plantilla sin llenar (ya lo avisa «sin llenar») y los espacios."""
    return texto.replace("«", "").replace("»", "").strip()


def _lleno(texto):
    return texto is not None and texto.strip() != "" and "«" not in texto and "»" not in texto


def _partir(valor):
    """Separa por comas, salvo las que están dentro de paréntesis: 'C2 (2,5), RF-004' -> ['C2 (2,5)', 'RF-004']."""
    partes, nivel, actual = [], 0, ""
    for c in valor:
        if c == "(":
            nivel += 1
        elif c == ")":
            nivel = max(0, nivel - 1)
        if c == "," and nivel == 0:
            partes.append(actual)
            actual = ""
        else:
            actual += c
    partes.append(actual)
    return [p.strip() for p in partes if p.strip()]


def _normalizado(valor):
    """Conjunto de elementos de un «Depende de:» o «Cubre:», para compararlos sin importar espacios ni orden."""
    v = _limpio(valor or "")
    if v in VACIOS:
        return frozenset()
    return frozenset(re.sub(r"\s+", "", t) for t in _partir(v))


def _clave(identificador):
    return int(re.search(r"\d+", identificador).group())


def _celdas(texto):
    return [c.strip() for c in texto.strip().strip("|").split("|")]


# ---- backlog (lo comparten PLAN.md y el docs/plan/backlog.md ya guardado) -----------
def leer_backlog(lineas, tipos, heads, ini, fin, nivel, error, aviso):
    """Lee las rebanadas y tareas de lineas[ini+1:fin] y las devuelve como (tareas, rebanadas).

    «nivel» es el nivel del título de cada rebanada: 3 en un PLAN.md y 2 en un docs/plan/backlog.md.
    """
    tareas, rebanadas = {}, {}
    por_linea = {h.i: h for h in heads if ini < h.i < fin}
    actual = None  # número de la rebanada en curso; -1 = una rebanada mal escrita (ya se avisó)
    marca = "#" * nivel
    for i in range(ini + 1, fin):
        if tipos[i] != "t":
            continue
        h = por_linea.get(i)
        if h is not None:
            if h.nivel != nivel:
                continue
            m = RE_REBANADA.match(h.titulo)
            if not m:
                error(i + 1, f"las rebanadas se escriben «{marca} Rebanada 1 · flujo que queda funcionando» "
                             f"(encontré «{marca} {h.titulo}»)")
                actual = -1
                continue
            num = int(m.group(1))
            if num in rebanadas:
                error(i + 1, f"la rebanada {num} está repetida (la primera vez está en la línea "
                             f"{rebanadas[num]['n']})")
            else:
                rebanadas[num] = {"flujo": m.group(2).strip(), "n": i + 1}
            actual = num
            continue
        if not RE_VINETA.match(lineas[i]):
            continue
        m = RE_TAREA.match(lineas[i].strip())
        if not m:
            error(i + 1, "la tarea debe escribirse «- T-001 · Título · Depende de: T-00x (o —) · Cubre: C1 (5), RF-001»")
            continue
        tid, titulo, dep, cub = m.group(1), m.group(2).strip(), m.group(3), m.group(4)
        if actual is None:
            error(i + 1, f"{tid}: esta tarea no está dentro de ninguna rebanada (agrega «{marca} Rebanada 1 · flujo» antes)")
        if " · " in titulo:
            error(i + 1, f"{tid}: el título no puede contener « · » (es el separador de la línea)")
        if tid in tareas:
            error(i + 1, f"{tid} está repetida (la primera vez está en la línea {tareas[tid]['n']})")
            continue
        depende, d = [], _limpio(dep)
        if not d:
            error(i + 1, f"{tid}: «Depende de:» no puede quedar vacío (usa — si no depende de ninguna tarea)")
        elif d not in VACIOS:
            for tok in _partir(d):
                if RE_ID_TAREA.match(tok):
                    depende.append(tok)
                else:
                    error(i + 1, f"{tid}: «Depende de:» cita «{tok}», que no es una tarea "
                                 "(usa T-001, o — si no depende de ninguna)")
        cubre, c = [], _limpio(cub)
        if not c:
            error(i + 1, f"{tid}: «Cubre:» no puede quedar vacío (usa — si no cubre nada)")
        elif c in VACIOS:
            aviso(i + 1, f"{tid}: no cubre ningún criterio ni requisito («Cubre: —»)")
        else:
            for tok in _partir(c):
                if RE_CUBRE.match(tok):
                    cubre.append(tok)
                else:
                    error(i + 1, f"{tid}: «Cubre:» cita «{tok}», que no es un criterio (C1 (5)) "
                                 "ni un requisito (RF-001, RN-01, RNF-01)")
        tareas[tid] = {"id": tid, "titulo": titulo, "depende": depende, "cubre": cubre, "dep_txt": d,
                       "cub_txt": c, "reb": actual if actual not in (None, -1) else None, "n": i + 1}
    return tareas, rebanadas


class BacklogGuardado:
    """Lo que dice el docs/plan/backlog.md que ya está en el repo."""

    def __init__(self, version, tareas, rebanadas):
        self.version, self.tareas, self.rebanadas = version, tareas, rebanadas


def leer_backlog_guardado(texto):
    """Lee un docs/plan/backlog.md. Lanza ValueError (con el motivo) si no se entiende."""
    lineas = texto.splitlines()
    tipos = idz.clasificar(lineas)
    heads = idz.encabezados(lineas, tipos)
    version = None
    for i, linea in enumerate(lineas):
        if tipos[i] == "t":
            m = RE_VERSION.match(linea.strip())
            if m:
                version = int(m.group(1))
                break
    if version is None:
        raise ValueError("no encuentro la línea «> Versión N · …»")
    problemas = []
    tareas, rebanadas = leer_backlog(lineas, tipos, heads, -1, len(lineas), 2,
                                     lambda n, m: problemas.append((n, m)), lambda n, m: None)
    if problemas:
        raise ValueError(f"línea {problemas[0][0]}: {problemas[0][1]}")
    if not tareas:
        raise ValueError("no tiene ninguna tarea")
    return BacklogGuardado(version, tareas, rebanadas)


class Contexto:
    """Lo que ya hay en el repo y condiciona el reparto."""

    def __init__(self, backlog=None, error_backlog=None, planes=(), tarjetas=(), rfs=None):
        self.backlog = backlog              # BacklogGuardado, o None si no hay (o no se pudo leer)
        self.error_backlog = error_backlog  # por qué no se pudo leer docs/plan/backlog.md
        self.planes = list(planes)          # de backlog.md y cobertura.md, los que ya existen
        self.tarjetas = set(tarjetas)       # IDs con archivo en docs/plan/tareas/
        self.rfs = rfs                      # IDs con archivo en docs/requisitos/, o None si no existe esa carpeta


def leer_contexto(raiz):
    backlog, error = None, None
    ruta = raiz / REL_BACKLOG
    if ruta.is_file():
        try:
            backlog = leer_backlog_guardado(ruta.read_bytes().decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as e:
            error = str(e) if isinstance(e, ValueError) else "no está en UTF-8"
    planes = [rel for rel in (REL_BACKLOG, REL_COBERTURA) if (raiz / rel).exists()]
    tareas_dir = raiz / "docs" / "plan" / "tareas"
    tarjetas = set()
    if tareas_dir.is_dir():
        tarjetas = {p.stem for p in tareas_dir.glob("*.md") if re.fullmatch(r"(?:T|REF)-\d+", p.stem)}
    rfs = None
    req = raiz / "docs" / "requisitos"
    if req.is_dir():
        rfs = set()
        for p in req.glob("RF-*.md"):
            m = re.match(r"(RF-\d+)", p.name)
            if m:
                rfs.add(m.group(1))
    return Contexto(backlog, error, planes, tarjetas, rfs)


# ---- análisis de un PLAN.md ---------------------------------------------------
class Plan:
    """Lee un PLAN.md, anota errores y avisos con número de línea y sabe repartirlo."""

    def __init__(self, texto):
        self.lineas = texto.splitlines()
        self.tipos = idz.clasificar(self.lineas)
        self.heads = idz.encabezados(self.lineas, self.tipos)
        self.errores = []     # (línea, mensaje); línea 0 = no corresponde a una línea concreta
        self.avisos = []
        self.conflictos = []  # mensajes: lo que hay (o falta) en el repo y impide repartir
        self.nombre = "(sin nombre)"
        self.cabecera = []
        self.version = None
        self.motivo = None
        self.secciones = {}   # clave -> (inicio, fin): índices de línea, fin excluido
        self.ola = None
        self.modo = None      # "completo" (con backlog y matriz) | "tarjetas" (solo una ola)
        self.tareas = {}
        self.rebanadas = {}
        self.tarjetas = []    # dicts: id, titulo, ini, fin, ref, n
        self.omitir = set()   # IDs de tarjetas que ya existen en el repo y no se pisan

    # ---- utilidades -------------------------------------------------------
    def error(self, n, msg):
        self.errores.append((n, msg))

    def aviso(self, n, msg):
        self.avisos.append((n, msg))

    def _fin_seccion(self, i):
        return next((h.i for h in self.heads if h.i > i and h.nivel <= 2), len(self.lineas))

    def _bloque(self, ini, fin):
        b = self.lineas[ini:fin]
        while b and not b[-1].strip():
            b.pop()
        return b

    # ---- análisis ---------------------------------------------------------
    def analizar(self, ctx=None):
        ctx = ctx or Contexto()
        if not any(l.strip() for l in self.lineas):
            self.error(0, "el archivo está vacío")
            return self
        self._secciones()
        self._titulo()
        if BACKLOG in self.secciones:
            self._backlog()
        if MATRIZ in self.secciones:
            self._matriz()
        self._leer_tarjetas()
        self._cruces(ctx)
        self._avisos_generales()
        return self

    def _secciones(self):
        for h in (x for x in self.heads if x.nivel == 2):
            if h.titulo in (BACKLOG, MATRIZ):
                clave = h.titulo
            elif RE_OLA.match(h.titulo):
                clave = TARJETAS_CLAVE
            elif h.titulo.startswith("Tarjetas de la ola"):
                self.error(h.i + 1, f"«## {h.titulo}»: falta el número de la ola, por ejemplo «## Tarjetas de la ola 1»")
                continue
            else:
                cerca = difflib.get_close_matches(h.titulo, [BACKLOG, MATRIZ, TARJETAS], n=1, cutoff=0.6)
                pista = f"; ¿quisiste decir «{cerca[0]}»?" if cerca else ""
                self.error(h.i + 1, f"sección desconocida «## {h.titulo}»{pista} "
                                    "Los títulos «##» deben ser exactamente los de la plantilla")
                continue
            if clave in self.secciones:
                if clave == TARJETAS_CLAVE:
                    self.error(h.i + 1, "solo puede haber una sección «## Tarjetas de la ola N» por archivo "
                                        f"(una ola por archivo; la primera está en la línea "
                                        f"{self.secciones[clave][0] + 1})")
                else:
                    self.error(h.i + 1, f"la sección «{h.titulo}» está repetida "
                                        f"(la primera está en la línea {self.secciones[clave][0] + 1})")
                continue
            self.secciones[clave] = (h.i, self._fin_seccion(h.i))
            if clave == TARJETAS_CLAVE:
                self.ola = int(RE_OLA.match(h.titulo).group(1))
        tiene_b, tiene_m = BACKLOG in self.secciones, MATRIZ in self.secciones
        if tiene_b != tiene_m:
            falta = MATRIZ if tiene_b else BACKLOG
            self.error(0, f"«## {BACKLOG}» y «## {MATRIZ}» van juntos: falta «## {falta}»")
        if TARJETAS_CLAVE not in self.secciones:
            self.error(0, f"falta la sección «## {TARJETAS}»")
        if tiene_b or tiene_m:
            self.modo = "completo"
        elif TARJETAS_CLAVE in self.secciones:
            self.modo = "tarjetas"

    def _titulo(self):
        h1 = [h for h in self.heads if h.nivel == 1]
        if not h1:
            if self.modo != "tarjetas":  # en las olas siguientes el título es opcional
                self.error(0, "falta el título «# PLAN — nombre de la app»")
            return
        primero = h1[0]
        previo = [i for i in range(primero.i) if self.tipos[i] != "m" and self.lineas[i].strip()]
        if previo:
            self.error(previo[0] + 1, "hay texto antes del título «# PLAN — nombre de la app»")
        m = RE_H1.match(primero.titulo)
        if m:
            self.nombre = m.group(1).strip()
        else:
            self.error(primero.i + 1, "el título debe ser «# PLAN — nombre de la app»")
        for extra in h1[1:]:
            self.error(extra.i + 1, "solo puede haber un título «#»; las secciones usan «##»")
        primer_h2 = next((h.i for h in self.heads if h.nivel == 2), len(self.lineas))
        self.cabecera = self._bloque(primero.i + 1, primer_h2)
        while self.cabecera and not self.cabecera[0].strip():
            self.cabecera.pop(0)
        if self.modo == "tarjetas":  # en las olas siguientes la cabecera es opcional y no se usa
            return
        linea_version = None
        for k in range(primero.i + 1, primer_h2):
            if self.tipos[k] != "t":
                continue
            texto = self.lineas[k].strip()
            mv, mm = RE_VERSION.match(texto), RE_MOTIVO.match(texto)
            if mv and self.version is None:
                self.version, linea_version = int(mv.group(1)), k + 1
            if mm:
                self.motivo = mm.group(1)
        if self.version is None:
            self.error(primero.i + 1, "falta la línea «> Versión 1 · fecha · fuente: DISENO.md, versión 1» "
                                      "bajo el título (la versión es un número)")
        elif self.version >= 2 and not _lleno(self.motivo):
            self.error(linea_version, f"la versión {self.version} replanifica el backlog: agrega la línea "
                                      "«> Motivo del cambio: …» con qué cambió y por qué")

    def _backlog(self):
        ini, fin = self.secciones[BACKLOG]
        self.tareas, self.rebanadas = leer_backlog(self.lineas, self.tipos, self.heads, ini, fin, 3,
                                                   self.error, self.aviso)
        if not self.tareas:
            self.error(ini + 1, "el backlog no tiene ninguna tarea: agrega "
                                "«- T-001 · Esqueleto andante · Depende de: — · Cubre: C1 (5)»")
        for t in self.tareas.values():
            for d in t["depende"]:
                if d == t["id"]:
                    self.error(t["n"], f"{t['id']}: no puede depender de sí misma")
                elif d not in self.tareas:
                    self.error(t["n"], f"{t['id']}: depende de {d}, que no está en el backlog")

    def _matriz(self):
        ini, fin = self.secciones[MATRIZ]
        filas = [(i, self.lineas[i]) for i in range(ini + 1, fin)
                 if self.tipos[i] == "t" and self.lineas[i].lstrip().startswith("|")]
        if not filas:
            self.error(ini + 1, "falta la tabla de la matriz: | Criterio | RF | Tareas |")
            return
        n0, cab = filas[0]
        c = [_limpio(x).lower() for x in _celdas(cab)]
        if c[:3] != ["criterio", "rf", "tareas"] or len(c) != 3:
            self.error(n0 + 1, "la cabecera de la tabla debe ser: | Criterio | RF | Tareas |")
        datos = filas[1:]
        if datos and re.fullmatch(r"[\s|:\-]+", datos[0][1]):
            datos = datos[1:]
        if not datos:
            self.error(n0 + 1, "la matriz no tiene ninguna fila")
        for i, t in datos:
            c = [_limpio(x) for x in _celdas(t)]
            if len(c) < 3:
                self.error(i + 1, "la fila debe tener 3 columnas: Criterio, RF y Tareas")
                continue
            if c[2] in VACIOS:
                continue
            ids = _partir(c[2])
            if not ids:
                self.error(i + 1, "la fila no tiene tareas (usa — si ninguna lo cubre todavía)")
            for tid in ids:
                if not RE_ID_TAREA.match(tid):
                    self.error(i + 1, f"«{tid}» no es una tarea (usa T-001)")
                elif BACKLOG in self.secciones and tid not in self.tareas:
                    self.error(i + 1, f"la fila cita {tid}, que no está en el backlog")

    def _texto_suelto(self, desde, hasta, donde):
        for i in range(desde, hasta):
            if self.tipos[i] != "m" and self.lineas[i].strip():
                self.aviso(i + 1, f"este texto no está dentro de ninguna {donde} y no se repartirá "
                                  "a ningún archivo (solo queda en docs/archivo/)")
                return

    def _leer_tarjetas(self):
        if TARJETAS_CLAVE not in self.secciones:
            return
        ini, fin = self.secciones[TARJETAS_CLAVE]
        subs = [h for h in self.heads if h.nivel == 3 and ini < h.i < fin]
        self._texto_suelto(ini + 1, subs[0].i if subs else fin, "tarjeta")
        if not subs:
            self.error(ini + 1, "no hay ninguna tarjeta: agrega «### T-001 · Título»")
            return
        for k, h in enumerate(subs):
            fin_b = subs[k + 1].i if k + 1 < len(subs) else fin
            m = RE_TARJETA.match(h.titulo)
            if not m:
                self.error(h.i + 1, f"las tarjetas se escriben «### T-001 · Título» (encontré «### {h.titulo}»)")
                continue
            tid = m.group(1)
            previo = next((t for t in self.tarjetas if t["id"] == tid), None)
            if previo:
                self.error(h.i + 1, f"{tid} está repetida (la primera vez está en la línea {previo['n']})")
                continue
            self.tarjetas.append({"id": tid, "titulo": f"{tid} · {m.group(2).strip()}", "ini": h.i,
                                  "fin": fin_b, "ref": tid.startswith("REF-"), "n": h.i + 1})

    def _datos_tarjeta(self, t):
        """(depende, cubre) como los escribe la tarjeta, o None si no tiene la línea «Estado: …»."""
        for i in range(t["ini"] + 1, t["fin"]):
            if self.tipos[i] != "t":
                continue
            linea = self.lineas[i].strip()
            if linea.startswith("Estado:"):
                dep = cub = None
                for parte in linea.split(" · "):
                    parte = parte.strip()
                    if parte.startswith("Depende de:"):
                        dep = parte[len("Depende de:"):]
                    elif parte.startswith("Cubre:"):
                        cub = parte[len("Cubre:"):]
                return dep, cub
        return None

    def _comparar(self, t, tarea):
        datos = self._datos_tarjeta(t)
        if datos is None or datos[0] is None or datos[1] is None:
            self.aviso(t["n"], f"{t['id']}: la tarjeta no trae la línea «Estado: … · Depende de: … · Cubre: …», "
                               "así que no pude compararla con el backlog")
            return
        dep, cub = datos
        if _normalizado(dep) != frozenset(tarea["depende"]):
            self.aviso(t["n"], f"{t['id']}: «Depende de:» de la tarjeta ({dep.strip()}) no coincide con el del "
                               f"backlog ({tarea['dep_txt']})")
        if _normalizado(cub) != _normalizado(tarea["cub_txt"]):
            self.aviso(t["n"], f"{t['id']}: «Cubre:» de la tarjeta ({cub.strip()}) no coincide con el del "
                               f"backlog ({tarea['cub_txt']})")

    def _cruces(self, ctx):
        """Lo que se comprueba con el backlog (el del propio archivo o el ya guardado) y con lo que hay en el repo."""
        if self.modo == "tarjetas":
            if ctx.backlog is None:
                if ctx.error_backlog:
                    self.conflictos.append(f"{REL_BACKLOG} existe pero no se pudo leer ({ctx.error_backlog})")
                else:
                    self.conflictos.append(f"no hay backlog guardado ({REL_BACKLOG}): una ola siguiente solo trae "
                                           "tarjetas y se verifica contra ese backlog; reparte antes el PLAN.md "
                                           "de la ola 1")
                return
            tareas, rebanadas, donde = ctx.backlog.tareas, ctx.backlog.rebanadas, REL_BACKLOG
        elif self.modo == "completo":
            tareas, rebanadas, donde = self.tareas, self.rebanadas, "el backlog"
        else:
            return
        linea_ola = self.secciones[TARJETAS_CLAVE][0] + 1 if TARJETAS_CLAVE in self.secciones else 0
        if self.ola is not None and rebanadas and self.ola not in rebanadas:
            self.error(linea_ola, f"la ola {self.ola} no existe en {donde} "
                                  f"(rebanadas: {', '.join(str(n) for n in sorted(rebanadas))})")
        if self.modo == "completo" and not tareas:
            return  # el backlog ya tiene errores: no llenar de errores en cascada
        for t in self.tarjetas:
            if t["id"] in ctx.tarjetas:
                self.omitir.add(t["id"])
                self.aviso(t["n"], f"{t['id']}: ya existe docs/plan/tareas/{t['id']}.md; no se pisa")
            if t["ref"]:
                continue  # las REF-NN no van en el backlog ni en la matriz
            tarea = tareas.get(t["id"])
            if tarea is None:
                self.error(t["n"], f"{t['id']}: esta tarjeta es de una tarea que no está en {donde}")
                continue
            if self.ola is not None and tarea["reb"] is not None and tarea["reb"] != self.ola:
                self.aviso(t["n"], f"{t['id']} es de la rebanada {tarea['reb']} y esta es la ola {self.ola}: "
                                   "solo la ola actual lleva tarjetas completas")
            self._comparar(t, tarea)
        if self.ola is not None:
            tiene = {t["id"] for t in self.tarjetas} | set(ctx.tarjetas)
            faltan = sorted((i for i, tt in tareas.items() if tt["reb"] == self.ola and i not in tiene), key=_clave)
            if faltan:
                self.aviso(linea_ola, f"faltan las tarjetas de {', '.join(faltan)} (rebanada {self.ola}); puedes "
                                      f"repartirlas después en un archivo con solo «## Tarjetas de la ola {self.ola}»")
        if self.modo == "completo":
            huerfanas = sorted((i for i in ctx.tarjetas if i.startswith("T-") and i not in self.tareas), key=_clave)
            if huerfanas:
                self.aviso(0, f"hay tarjetas guardadas de tareas que ya no están en el backlog nuevo: "
                              f"{', '.join(huerfanas)} (revísalas; no se borran solas)")
            self._avisos_rf(ctx)

    def _avisos_rf(self, ctx):
        if ctx.rfs is None:
            return
        citados = {}
        for t in self.tareas.values():
            for tok in t["cubre"]:
                if tok.startswith("RF-"):
                    citados.setdefault(tok, []).append(t["id"])
        if not citados:
            return
        if not ctx.rfs:
            self.aviso(0, "docs/requisitos/ no tiene ningún requisito: ¿repartiste ya el DISENO.md con "
                          "init_diseno.py? No pude comprobar los RF que cita «Cubre:»")
            return
        faltan = sorted((rf for rf in citados if rf not in ctx.rfs), key=_clave)
        if faltan:
            detalle = ", ".join(f"{rf} ({', '.join(citados[rf])})" for rf in faltan)
            self.aviso(0, f"«Cubre:» cita requisitos sin archivo en docs/requisitos/: {detalle}")

    def _avisos_generales(self):
        sin_llenar = [i for i, l in enumerate(self.lineas) if self.tipos[i] == "t" and ("«" in l or "»" in l)]
        for i in sin_llenar[:5]:
            self.aviso(i + 1, "parece un campo de la plantilla sin llenar: " + self.lineas[i].strip()[:60])
        if len(sin_llenar) > 5:
            self.aviso(0, f"…y {len(sin_llenar) - 5} campo(s) más sin llenar")

    # ---- reparto ----------------------------------------------------------
    def choques(self, ctx, force=False):
        """Mensajes de lo que impide repartir por cómo está el repo (no por el formato del plan)."""
        salida = list(self.conflictos)
        if self.modo == "completo" and ctx.planes and not force:
            guardada = ctx.backlog.version if ctx.backlog else None
            if guardada is None:
                salida.append(f"ya existe {' y '.join(ctx.planes)} y no pude leer la versión guardada; "
                              "usa --force si quieres reemplazarlos")
            elif self.version == guardada:
                salida.append(f"el backlog guardado ya es la versión {guardada}: ese plan ya está repartido. Para "
                              f"replanificar sube la versión a {guardada + 1} y agrega «Motivo del cambio:» "
                              "(con --force se reemplaza igual)")
            elif self.version != guardada + 1:
                salida.append(f"la versión es {self.version} y la guardada es {guardada}: una replanificación "
                              f"debe ser la {guardada + 1} (con --force se reemplaza igual)")
        return salida

    def reparto(self):
        """Lista de (ruta relativa, texto) que se escribirían. Solo vale si no hay errores."""
        salida = []
        if self.modo == "completo":
            ini, fin = self.secciones[BACKLOG]
            niveles = {h.i: h for h in self.heads if ini < h.i < fin and h.nivel == 3}
            cuerpo = [("## " + niveles[i].titulo) if i in niveles else self.lineas[i] for i in range(ini + 1, fin)]
            while cuerpo and not cuerpo[-1].strip():
                cuerpo.pop()
            while cuerpo and not cuerpo[0].strip():
                cuerpo.pop(0)
            encabezado = self.cabecera + [""] if self.cabecera else []
            salida.append((REL_BACKLOG, idz._unir([f"# Backlog — {self.nombre}", ""] + encabezado + cuerpo + [""])))
            ini, fin = self.secciones[MATRIZ]
            salida.append((REL_COBERTURA, idz._unir([f"# Cobertura — {self.nombre}", ""] + encabezado
                                                    + self._bloque(ini, fin) + [""])))
        for t in self.tarjetas:
            if t["id"] in self.omitir:
                continue
            b = self._bloque(t["ini"], t["fin"])
            b[0] = "# " + t["titulo"]
            salida.append((f"docs/plan/tareas/{t['id']}.md", idz._unir(b)))
        return salida


# ---- línea de comandos ----------------------------------------------------
def _situacion(p, ctx):
    if p.modo == "tarjetas":
        return (f"Solo tarjetas de la ola {p.ola}: se verificaron contra el backlog guardado "
                f"(versión {ctx.backlog.version}).")
    if ctx.backlog is None and not ctx.planes:
        return f"Primer reparto del plan (versión {p.version})."
    if ctx.backlog is not None and p.version == ctx.backlog.version + 1:
        return f"Replanificación: versión {ctx.backlog.version} → {p.version}. Se reemplazan backlog.md y cobertura.md."
    return "Se reemplazan backlog.md y cobertura.md (--force)."


def _escribir(raiz, archivos, ruta, archivo_orig):
    """Escribe todo o nada: si algo falla, borra lo que creó y devuelve a su contenido lo que reemplazó."""
    previos = {raiz / rel: (raiz / rel).read_bytes() for rel, _ in archivos if (raiz / rel).is_file()}
    nuevos = []
    try:
        for rel, contenido in archivos:
            dest = raiz / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest not in previos:
                nuevos.append(dest)
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(contenido)
        archivo_orig.parent.mkdir(parents=True, exist_ok=True)
        nuevos.append(archivo_orig)
        shutil.copyfile(ruta, archivo_orig)
        if archivo_orig.read_bytes() != ruta.read_bytes():
            raise OSError("la copia en docs/archivo/ no coincide con el original")
    except OSError:
        for p in nuevos:
            try:
                p.unlink()
            except OSError:
                pass
        for p, antes in previos.items():
            try:
                p.write_bytes(antes)
            except OSError:
                pass
        raise
    return sorted(previos)


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):  # que una consola con otra codificación no tumbe el programa
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="init_plan.py", description="Reparte PLAN.md en docs/plan/ y revisa su formato.")
    ap.add_argument("archivo", help="ruta del PLAN.md (o de PLAN-ola2.md, PLAN-v2.md…)")
    ap.add_argument("--check", action="store_true", help="solo revisa: no escribe nada y muestra qué se repartiría")
    ap.add_argument("--force", action="store_true",
                    help="acepta un plan completo aunque ya haya un backlog guardado (nunca pisa tarjetas)")
    args = ap.parse_args(argv)

    raiz = Path(__file__).resolve().parent.parent
    ruta = Path(args.archivo)
    if not ruta.is_file():
        print(f"No encuentro el archivo «{args.archivo}». Corre el comando desde la raíz del repo "
              "y revisa el nombre.")
        return 2
    try:
        texto = ruta.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        print(f"{args.archivo}: el archivo no está en UTF-8. Guárdalo como UTF-8 y vuelve a intentar.")
        return 1

    ctx = leer_contexto(raiz)
    p = Plan(texto).analizar(ctx)
    idz._mostrar("Errores", p.errores, args.archivo)
    idz._mostrar("Avisos", p.avisos, args.archivo)
    if p.errores:
        print(f"\nEl formato tiene {len(p.errores)} error(es). No se escribió nada. "
              f"Corrige el {ruta.name} y vuelve a correr el comando.")
        return 1

    archivo_orig = raiz / "docs" / "archivo" / ruta.name
    if ruta.resolve() == archivo_orig.resolve():
        print("Ese archivo ya está en docs/archivo/. Pásame el original.")
        return 2
    choques = p.choques(ctx, args.force)
    if archivo_orig.exists():
        choques.append(f"docs/archivo/{ruta.name} ya existe: los planes archivados no se pisan, ni con --force. "
                       "Dale otro nombre a este archivo (PLAN-v2.md si replanifica, PLAN-ola3.md si es otra ola)")
    if choques:
        print("\nNo se escribió nada:")
        for c in choques:
            print(f"  {c}")
        return 2

    reparto = p.reparto()
    if p.modo == "completo":
        detalle = (f"{idz._cuenta(len(p.tareas), 'tarea', 'tareas')} en "
                   f"{idz._cuenta(len(p.rebanadas), 'rebanada', 'rebanadas')}, "
                   f"{idz._cuenta(len(p.tarjetas), 'tarjeta', 'tarjetas')}")
    else:
        detalle = f"ola {p.ola}: {idz._cuenta(len(p.tarjetas), 'tarjeta', 'tarjetas')}"
    print(f"\n{args.archivo}: formato correcto ({detalle}).")
    print(_situacion(p, ctx))
    reemplazados = [rel for rel, _ in reparto if (raiz / rel).exists()]

    if args.check:
        print("\nModo --check: no se escribió nada. Esto es lo que se repartiría:")
        for rel, contenido in reparto:
            marca = "  (reemplaza el actual)" if rel in reemplazados else ""
            print(f"  {rel}  ({len(contenido.splitlines())} líneas){marca}")
        print(f"  docs/archivo/{ruta.name}  (copia del original)")
        if p.omitir:
            print(f"\nNo se tocarían {len(p.omitir)} tarjeta(s) que ya existen: {', '.join(sorted(p.omitir, key=_clave))}.")
        return 0

    try:
        _escribir(raiz, reparto, ruta, archivo_orig)
    except OSError as e:
        print(f"\nNo pude escribir los archivos ({e}). Deshice lo que alcancé a crear.")
        return 2

    print("\nArchivos creados:")
    for rel, contenido in reparto:
        if rel not in reemplazados:
            print(f"  {rel}  ({len(contenido.splitlines())} líneas)")
    if reemplazados:
        print("Archivos reemplazados:")
        for rel in reemplazados:
            print(f"  {rel}")
    if p.omitir:
        print(f"No se tocaron {len(p.omitir)} tarjeta(s) que ya existían: {', '.join(sorted(p.omitir, key=_clave))}.")
    movido = ruta.resolve().parent == raiz
    if movido:
        ruta.unlink()
        print(f"  docs/archivo/{ruta.name}  (el original se movió desde la raíz del repo)")
    else:
        print(f"  docs/archivo/{ruta.name}  (copia; tu archivo original no se tocó)")
    print("\nSiguiente paso: revisa con «git status» y «git diff»; si está bien, haz commit y push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
