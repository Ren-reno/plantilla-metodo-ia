#!/usr/bin/env python3
"""Revisa que diseño, plan, tarjetas y código sean coherentes entre sí. Solo usa la biblioteca estándar.

Uso, desde la raíz del repo:
    python tools/validar.py            revisa diseño, backlog, matriz de cobertura y tarjetas
    python tools/validar.py --estricto trata avisos como errores
    python tools/validar.py --repo DIR revisa otro repositorio (por defecto, la raíz del repo actual)

Comprueba:
    1. Grafo de dependencias y ciclos en el backlog (no hay tareas que dependan de sí mismas,
       tareas inexistentes ni cadenas cíclicas como A -> B -> A).
    2. Cobertura de requisitos y criterios: ningún RF en docs/requisitos/ queda huérfano; todo
       criterio de éxito de contexto.md está cubierto en el backlog.
    3. Matriz de cobertura: la tabla de docs/plan/cobertura.md coincide con el backlog
       (no falta ni sobra ninguna relación criterio-RF-tarea).
    4. Tarjetas de docs/plan/tareas/:
       - Máximo de 4 criterios de aceptación (D16: si pasa de 4 sube de camino o debe partirse).
       - «Peso:», si la tarjeta lo declara: avisa cuando declara dos o más resultados independientes,
         porque la regla de partición dice partirla. Es aviso: partir o conservar lo decide la persona.
       - Campo «Fuera de alcance:» presente y explícito (D16).
       - Coherencia con el backlog («Depende de:» y «Cubre:» idénticos a los de su línea del backlog).
       - Archivos citados en «Leer:» existen con su grafía exacta, o indican «(lo produce T-xxx)».
         Es error, no aviso: bundle.py se niega en el mismo caso. La grafía se compara con el
         disco porque Windows no distingue mayúsculas y el CI en Linux sí.
       - ADRs citados existen; si están en «propuesta», avisa que bloquean bundle.py (D14); si están
         «reemplazada», es error: ahí no hay nada que decidir, la tarjeta cita una decisión sustituida.
       - En tarjetas REF-NN: solo tocan código (nunca tests ni docs).
    5. Estructura y alertas de refactor (D37): avisa si hay archivos de código muy grandes (>500 líneas)
       como candidatos a evaluar en el chat de hito.

Códigos de salida:
    0  todo coherente (puede haber avisos)
    1  se encontraron errores de coherencia (o avisos con --estricto)
    2  problema de uso o repositorio sin inicializar (falta docs/ o docs/plan/backlog.md)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path, PurePosixPath

# Permitir importar herramientas hermanas desde tools/
_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import init_diseno as idz
import init_plan as ip

# Límites fijados por el método (D16, D37)
MAX_CRITERIOS_TARJETA = 4
MAX_LINEAS_CODIGO_AVISO = 500

RE_ID_TAREA = re.compile(r"^T-\d+$")
RE_ID_REF = re.compile(r"^REF-\d+$")
RE_ID_RF = re.compile(r"^RF-\d+$")
RE_ID_CRITERIO = re.compile(r"^[CR]\d+$")
RE_CRITERIO_TOKEN = re.compile(r"^([CR]\d+)(?:\s*\(\d+\))?$")
RE_ADR_TOKEN = re.compile(r"^(?:docs/decisiones/)?(\d{4})-[a-z0-9\-]+\.md$")
RE_ESTADO_ADR = re.compile(r"^Estado:\s*(\S+)")
RE_SECCION_CRITERIOS_TARJETA = re.compile(r"^Criterios de aceptación\s*(?:\(→\s*tests\))?:")
RE_SECCION_FUERA_ALCANCE = re.compile(r"^Fuera de alcance:\s*(.*)$")
# «Peso:» cuenta resultados independientes. No mide esfuerzo por número de criterios, que se
# cumple comprimiendo varias comprobaciones en una viñeta.
RE_PESO_RESULTADOS = re.compile(r"(\d+)\s+resultados?\b", re.IGNORECASE)


def normalizar_criterio(tok: str) -> str:
    """Extrae el identificador base de un criterio (ej. 'C1 (5)' -> 'C1')."""
    m = RE_CRITERIO_TOKEN.match(tok.strip())
    return m.group(1) if m else tok.strip()


def detectar_ciclos(grafo: dict[str, list[str]]) -> list[list[str]]:
    """Encuentra ciclos en un grafo dirigido. Cada ciclo es [A, B, ..., A]."""
    estado: dict[str, int] = {}  # 0: no visitado, 1: en progreso, 2: terminado
    camino: list[str] = []
    ciclos: list[list[str]] = []

    def dfs(u: str):
        estado[u] = 1
        camino.append(u)
        for v in sorted(grafo.get(u, [])):
            if v not in grafo:
                continue
            if estado.get(v, 0) == 1:
                idx = camino.index(v)
                ciclos.append(camino[idx:] + [v])
            elif estado.get(v, 0) == 0:
                dfs(v)
        camino.pop()
        estado[u] = 2

    for nodo in sorted(grafo.keys()):
        if estado.get(nodo, 0) == 0:
            dfs(nodo)

    return ciclos


def ruta_real(raiz: Path, rel: str) -> str | None:
    """La ruta tal como está escrita en el disco, o None si no existe.

    Hace falta porque en Windows `Path.exists()` no distingue mayúsculas: una tarjeta puede
    citar «docs/experiencia.md» y pasar la validación local mientras el CI en Linux no
    encuentra el archivo, que se llama «docs/EXPERIENCIA.md». Compara segmento a segmento
    con lo que hay en el disco para que local y CI digan lo mismo.
    """
    actual = raiz
    partes: list[str] = []
    for parte in PurePosixPath(rel).parts:
        try:
            nombres = {p.name for p in actual.iterdir()}
        except OSError:
            return None
        if parte in nombres:
            real = parte
        else:
            iguales = sorted(n for n in nombres if n.lower() == parte.lower())
            if not iguales:
                return None
            real = iguales[0]
        partes.append(real)
        actual = actual / real
    return "/".join(partes)


class Validador:
    """Revisa la coherencia integral entre diseño, plan, cobertura, tarjetas y código."""

    def __init__(self, raiz: Path, estricto: bool = False):
        self.raiz = raiz.resolve()
        self.estricto = estricto
        self.errores: list[str] = []
        self.avisos: list[str] = []

        # Estado cargado del repo
        self.criterios_diseno: dict[str, dict] = {}
        self.reglas_diseno: dict[str, str] = {}   # RN/RNF de contexto.md, por identificador
        self.rfs_diseno: dict[str, dict] = {}
        self.adrs_diseno: dict[str, str] = {}  # num -> estado ("propuesta", "aceptada", etc.)
        self.backlog: ip.BacklogGuardado | None = None
        self.filas_matriz: list[dict] = []
        self.tarjetas: dict[str, dict] = {}

    def error(self, msg: str):
        self.errores.append(msg)

    def aviso(self, msg: str):
        self.avisos.append(msg)

    def cargar(self) -> int:
        """Carga los archivos del arnés. Retorna 0 si todo está listo para validar, o 2 si falta algo crítico."""
        docs = self.raiz / "docs"
        if not docs.is_dir():
            print(f"No encuentro la carpeta «docs/» en {self.raiz}. Corre el comando desde la raíz del repo.")
            return 2

        rel_backlog = self.raiz / ip.REL_BACKLOG
        if not rel_backlog.is_file():
            print(f"No encuentro {ip.REL_BACKLOG}. El plan no ha sido repartido todavía (usa init_plan.py).")
            return 2

        # 1. Cargar contexto y requisitos
        self._cargar_requisitos()

        # 2. Cargar decisiones (ADRs)
        self._cargar_adrs()

        # 3. Cargar backlog
        try:
            texto_backlog = rel_backlog.read_bytes().decode("utf-8-sig")
            self.backlog = ip.leer_backlog_guardado(texto_backlog)
        except Exception as e:
            print(f"Error al leer {ip.REL_BACKLOG}: {e}")
            return 2

        # 4. Cargar matriz de cobertura
        rel_cobertura = self.raiz / ip.REL_COBERTURA
        if rel_cobertura.is_file():
            texto_matriz = rel_cobertura.read_bytes().decode("utf-8-sig")
            self._cargar_matriz(texto_matriz)

        # 5. Cargar tarjetas
        self._cargar_tarjetas()

        return 0

    def _cargar_requisitos(self):
        ctx_file = self.raiz / "docs" / "requisitos" / "contexto.md"
        if ctx_file.is_file():
            texto = ctx_file.read_bytes().decode("utf-8-sig")
            filas = [l.strip() for l in texto.splitlines() if l.strip().startswith("|")]
            for fila in filas:
                celdas = [c.strip() for c in fila.split("|")[1:-1]]
                if len(celdas) >= 3 and RE_ID_CRITERIO.match(celdas[0]):
                    cid = celdas[0]
                    desc = celdas[1]
                    peso = celdas[2]
                    self.criterios_diseno[cid] = {"id": cid, "desc": desc, "peso": peso}
            self.reglas_diseno = idz.reglas_declaradas(texto)

        req_dir = self.raiz / "docs" / "requisitos"
        if req_dir.is_dir():
            for p in sorted(req_dir.glob("RF-*.md")):
                rf_id = p.name.split("-")[0] + "-" + p.name.split("-")[1]
                texto = p.read_bytes().decode("utf-8-sig")
                aporta: list[str] = []
                for l in texto.splitlines():
                    m = idz.RE_APORTA.match(l.strip())
                    if m:
                        aporta = [x.strip() for x in m.group(1).split(",") if x.strip()]
                        break
                self.rfs_diseno[rf_id] = {"id": rf_id, "archivo": p.name, "aporta": aporta}

    def _cargar_adrs(self):
        dec_dir = self.raiz / "docs" / "decisiones"
        if dec_dir.is_dir():
            for p in sorted(dec_dir.glob("*.md")):
                if p.name == "README.md" or p.name.startswith("."):
                    continue
                m = re.match(r"^(\d{4})-", p.name)
                if m:
                    num = m.group(1)
                    texto = p.read_bytes().decode("utf-8-sig")
                    estado = "desconocido"
                    for l in texto.splitlines():
                        m_est = RE_ESTADO_ADR.search(l)
                        if m_est:
                            estado = m_est.group(1).strip().lower()
                            break
                    self.adrs_diseno[num] = estado

    def _cargar_matriz(self, texto: str):
        lineas = texto.splitlines()
        filas = [l.strip() for l in lineas if l.strip().startswith("|")]
        if len(filas) < 2:
            return
        # Omitir cabecera y separador
        for f in filas:
            celdas = [c.strip() for c in f.split("|")[1:-1]]
            if len(celdas) >= 3:
                c0 = celdas[0].lower()
                if c0 in ("criterio", "id") or re.fullmatch(r"[\s|:\-]+", f):
                    continue
                criterio = normalizar_criterio(celdas[0])
                rf = celdas[1]
                t_str = celdas[2]
                tareas = [t.strip() for t in t_str.split(",") if t.strip() and t.strip() not in ip.VACIOS]
                self.filas_matriz.append({"criterio": criterio, "rf": rf, "tareas": tareas})

    def _cargar_tarjetas(self):
        tareas_dir = self.raiz / "docs" / "plan" / "tareas"
        if not tareas_dir.is_dir():
            return
        for p in sorted(tareas_dir.glob("*.md")):
            if p.name.startswith("."):
                continue
            tid = p.stem
            texto = p.read_bytes().decode("utf-8-sig")
            lineas = texto.splitlines()

            # Leer campos básicos
            depende: list[str] = []
            cubre: list[str] = []
            fuera_de_alcance: str | None = None
            peso: str | None = None
            criterios: list[str] = []
            leer: list[str] = []
            tocar: list[str] = []

            en_criterios = False
            for i, l in enumerate(lineas):
                l_s = l.strip()
                if l_s.startswith("Estado:"):
                    # Parsear Depende de: y Cubre:
                    partes = l_s.split(" · ")
                    for parte in partes:
                        parte = parte.strip()
                        if parte.startswith("Depende de:"):
                            val = parte[len("Depende de:"):].strip()
                            if val not in ip.VACIOS:
                                depende = [t.strip() for t in val.split(",") if t.strip()]
                        elif parte.startswith("Cubre:"):
                            val = parte[len("Cubre:"):].strip()
                            if val not in ip.VACIOS:
                                cubre = [t.strip() for t in val.split(",") if t.strip()]
                elif l_s.startswith("Fuera de alcance:"):
                    fuera_de_alcance = l_s[len("Fuera de alcance:"):].strip()
                elif l_s.startswith("Peso:"):
                    peso = l_s[len("Peso:"):].strip()
                elif l_s.startswith("Leer (solo esto):"):
                    val = l_s[len("Leer (solo esto):"):].strip()
                    leer = [x.strip() for x in val.split(" · ") if x.strip()]
                elif l_s.startswith("Tocar:"):
                    val = l_s[len("Tocar:"):].strip()
                    tocar = [x.strip() for x in val.split(" · ") if x.strip()]
                elif RE_SECCION_CRITERIOS_TARJETA.match(l_s):
                    en_criterios = True
                    continue
                elif en_criterios:
                    if l_s.startswith("- "):
                        criterios.append(l_s[2:].strip())
                    elif l_s.startswith(("#", "Ejemplos aprobados:", "Comando de test:", "Entrega:")):
                        en_criterios = False

            self.tarjetas[tid] = {
                "id": tid,
                "archivo": p.name,
                "depende": depende,
                "cubre": cubre,
                "fuera_de_alcance": fuera_de_alcance,
                "peso": peso,
                "criterios": criterios,
                "leer": leer,
                "tocar": tocar,
            }

    def validar(self) -> tuple[list[str], list[str]]:
        """Ejecuta todos los chequeos de coherencia y retorna (errores, avisos)."""
        self.errores.clear()
        self.avisos.clear()

        if self.backlog is None:
            return self.errores, self.avisos

        self._validar_grafo_backlog()
        self._validar_cobertura_requisitos()
        self._validar_matriz_cobertura()
        self._validar_tarjetas()
        self._validar_codigo()

        return self.errores, self.avisos

    def _validar_grafo_backlog(self):
        """Verifica que no haya ciclos, tareas inexistentes ni auto-dependencias."""
        tareas = self.backlog.tareas
        grafo: dict[str, list[str]] = {}

        for tid, t in sorted(tareas.items()):
            grafo[tid] = []
            for dep in t["depende"]:
                if dep == tid:
                    self.error(f"{tid}: depende de sí misma en el backlog.")
                elif dep not in tareas:
                    self.error(f"{tid}: depende de «{dep}», que no existe en el backlog.")
                else:
                    grafo[tid].append(dep)
                    # Advertir si depende de una rebanada posterior
                    reb_actual = t.get("reb")
                    reb_dep = tareas[dep].get("reb")
                    if reb_actual is not None and reb_dep is not None and reb_dep > reb_actual:
                        self.aviso(f"{tid} (Rebanada {reb_actual}) depende de {dep} (Rebanada posterior {reb_dep}).")

        ciclos = detectar_ciclos(grafo)
        for c in ciclos:
            cadena = " -> ".join(c)
            self.error(f"Ciclo de dependencias detectado en el backlog: {cadena}.")

    def _validar_cobertura_requisitos(self):
        """Verifica que ningún RF de docs/requisitos/ ni criterio de éxito quede huérfano."""
        tareas = self.backlog.tareas
        rfs_cubiertos = set()
        criterios_cubiertos = set()

        for tid, t in tareas.items():
            for tok in t["cubre"]:
                norm_c = normalizar_criterio(tok)
                if RE_ID_CRITERIO.match(norm_c):
                    criterios_cubiertos.add(norm_c)
                if RE_ID_RF.match(tok):
                    rfs_cubiertos.add(tok)

        # 1. Comprobar RFs huérfanos
        for rf_id, rf_info in sorted(self.rfs_diseno.items()):
            if rf_id not in rfs_cubiertos:
                self.error(f"El requisito {rf_id} («{rf_info['archivo']}») no está cubierto por ninguna tarea en el backlog.")

        # 2. Comprobar criterios huérfanos de contexto.md
        for cid in sorted(self.criterios_diseno.keys()):
            if cid not in criterios_cubiertos:
                self.error(f"El criterio de éxito {cid} (de docs/requisitos/contexto.md) no está cubierto por ninguna tarea en el backlog.")

        # 3. Comprobar RFs citados en el backlog que no existen en docs/requisitos/
        if self.rfs_diseno:
            for tid, t in sorted(tareas.items()):
                for tok in t["cubre"]:
                    if RE_ID_RF.match(tok) and tok not in self.rfs_diseno:
                        self.aviso(f"{tid}: cubre «{tok}», pero no existe archivo correspondiente en docs/requisitos/.")

    def _validar_matriz_cobertura(self):
        """Compara la matriz escrita en cobertura.md contra el backlog."""
        if not self.filas_matriz:
            return

        tareas_backlog = self.backlog.tareas

        # Cada tarea en la matriz debe existir en el backlog
        for fila in self.filas_matriz:
            crit = fila["criterio"]
            rf = fila["rf"]
            for tid in fila["tareas"]:
                if tid not in tareas_backlog:
                    self.error(f"docs/plan/cobertura.md: la fila {crit} | {rf} cita «{tid}», que no está en el backlog.")
                else:
                    t_cub = [normalizar_criterio(x) for x in tareas_backlog[tid]["cubre"]]
                    # La tarea debe cubrir al menos el criterio o el RF
                    cubre_crit = crit in t_cub
                    cubre_rf = rf in t_cub or rf in ip.VACIOS
                    if not cubre_crit and not cubre_rf:
                        self.error(f"docs/plan/cobertura.md: la fila {crit} | {rf} cita «{tid}», pero esa tarea no cubre ni {crit} ni {rf} en el backlog.")

        # Comprobar que toda combinación (Criterio, RF) declarada en una tarea esté en la matriz
        for tid, t in sorted(tareas_backlog.items()):
            crits_tarea = [normalizar_criterio(x) for x in t["cubre"] if RE_ID_CRITERIO.match(normalizar_criterio(x))]
            rfs_tarea = [x for x in t["cubre"] if RE_ID_RF.match(x)]

            for c in crits_tarea:
                for rf in rfs_tarea:
                    # Si conocemos a qué criterios aporta este RF, solo exigir la fila si el RF aporta a c
                    if rf in self.rfs_diseno and self.rfs_diseno[rf]["aporta"]:
                        if c not in self.rfs_diseno[rf]["aporta"]:
                            continue

                    # Debe haber una fila (c, rf) que contenga tid
                    encontrada = False
                    for fila in self.filas_matriz:
                        if fila["criterio"] == c and fila["rf"] == rf:
                            if tid in fila["tareas"]:
                                encontrada = True
                            break
                    if not encontrada:
                        self.error(f"docs/plan/cobertura.md: falta reflejar que {tid} cubre {c} | {rf} (declarado en el backlog).")

    def _validar_tarjetas(self):
        """Verifica el arnés en las tarjetas: <= 4 criterios, Fuera de alcance, y coherencia."""
        tareas_backlog = self.backlog.tareas

        for tid, t_card in sorted(self.tarjetas.items()):
            # 1. Regla D16: Máximo 4 criterios de aceptación
            num_crits = len(t_card["criterios"])
            if num_crits > MAX_CRITERIOS_TARJETA:
                self.error(f"{tid}: tiene {num_crits} criterios de aceptación (el arnés fija un máximo de {MAX_CRITERIOS_TARJETA}; D16).")
            elif num_crits == 0:
                self.error(f"{tid}: no tiene criterios de aceptación en su tarjeta.")

            # 1b. «Peso:», si la tarjeta lo declara: dos resultados separables se parten
            peso = t_card.get("peso")
            if peso:
                m_peso = RE_PESO_RESULTADOS.search(peso)
                if m_peso and int(m_peso.group(1)) >= 2:
                    self.aviso(f"{tid}: su «Peso:» declara {m_peso.group(1)} resultados independientes; "
                               "la regla de partición dice partir la tarea, o explicar en el objetivo por qué "
                               "conservarla entera.")

            # 2. Regla D16: Fuera de alcance obligatorio
            fa = t_card["fuera_de_alcance"]
            if fa is None or not fa.strip() or fa.strip() in ip.VACIOS or idz.solo_huecos(fa):
                self.error(f"{tid}: falta el campo «Fuera de alcance:» (debe indicar explícitamente qué NO se construye; D16).")

            # 2b. Una regla citada por un criterio tiene que existir: si no, el bundle la inventa
            for rid in idz.citas_de_reglas(" · ".join(t_card["criterios"] or [])):
                if rid not in self.reglas_diseno:
                    self.aviso(f"{tid}: un criterio cita {rid}, que no está declarado en «Reglas y "
                               "restricciones» del diseño. bundle.py se negará a armar su paquete, porque una "
                               "tarea no puede cumplir una regla que nadie escribió.")

            # 3. Coherencia con el backlog
            if RE_ID_TAREA.match(tid):
                if tid not in tareas_backlog:
                    self.error(f"{tid}: la tarjeta existe en docs/plan/tareas/, pero la tarea no está en el backlog.")
                else:
                    t_b = tareas_backlog[tid]
                    # Comparar Depende de
                    dep_card = sorted(t_card["depende"])
                    dep_b = sorted(t_b["depende"])
                    if dep_card != dep_b:
                        self.error(f"{tid}: «Depende de:» en la tarjeta ({', '.join(dep_card) or '—'}) "
                                   f"no coincide con el backlog ({', '.join(dep_b) or '—'}).")

                    # Comparar Cubre
                    cub_card = sorted(normalizar_criterio(x) for x in t_card["cubre"])
                    cub_b = sorted(normalizar_criterio(x) for x in t_b["cubre"])
                    if cub_card != cub_b:
                        self.error(f"{tid}: «Cubre:» en la tarjeta ({', '.join(cub_card) or '—'}) "
                                   f"no coincide con el backlog ({', '.join(cub_b) or '—'}).")

            elif RE_ID_REF.match(tid):
                # Tarjeta de refactor: no debe tocar tests ni docs
                for item in t_card["tocar"]:
                    ruta = item.split("(")[0].strip()
                    if ruta.startswith(("tests/", "docs/", "tests\\", "docs\\")):
                        self.error(f"{tid}: es una tarjeta de refactor (REF), pero «Tocar:» incluye «{ruta}» (solo debe tocar código de producción; D37).")

            # 4. Comprobar archivos citados en Leer:
            for item in t_card["leer"]:
                crudo = item.split("(")[0].strip()
                ruta_limpia, _, ancla = crudo.partition("#")
                if not ruta_limpia or "«" in ruta_limpia:
                    continue
                # Si cita un ADR
                m_adr = RE_ADR_TOKEN.search(ruta_limpia)
                if m_adr:
                    num_adr = m_adr.group(1)
                    if num_adr not in self.adrs_diseno:
                        self.error(f"{tid}: cita en «Leer:» el ADR-{num_adr}, pero no existe archivo correspondiente en docs/decisiones/.")
                    elif self.adrs_diseno[num_adr] == "propuesta":
                        # Aviso, no error: aceptar una decisión es tuyo y el plan puede validarse antes.
                        self.aviso(f"{tid}: cita en «Leer:» el ADR-{num_adr} que está en estado «propuesta» (bloqueará bundle.py; D14).")
                    elif self.adrs_diseno[num_adr] == "reemplazada":
                        # Error: aquí no hay nada pendiente de decidir, la tarjeta cita una
                        # decisión sustituida. bundle.py también se niega (D14).
                        self.error(f"{tid}: cita en «Leer:» el ADR-{num_adr}, que está «reemplazada»: "
                                   "debe citar la decisión que la reemplaza (bundle.py se negará a armar su bundle).")
                elif "(lo produce T-" not in item:
                    # Archivo general. Es error, no aviso: bundle.py se niega a armar el bundle
                    # en este mismo caso, así que avisarlo aquí y dejar pasar el CI solo retrasa
                    # el bloqueo. La grafía se comprueba aparte porque Windows no la distingue.
                    real = ruta_real(self.raiz, ruta_limpia)
                    if real is None:
                        self.error(f"{tid}: cita en «Leer:» «{ruta_limpia}», que no existe en el repo ni indica "
                                   "qué tarea lo produce (bundle.py se negará a armar su bundle).")
                    elif real != ruta_limpia:
                        self.error(f"{tid}: cita en «Leer:» «{ruta_limpia}», pero el archivo versionado es "
                                   f"«{real}». Windows resuelve las dos; Linux y el CI solo la segunda.")

            # 5. Comprobar tamaño de Tocar (aislamiento de módulo)
            modulos_tocados = set()
            for item in t_card["tocar"]:
                crudo = item.split("(")[0].strip()
                partes = Path(crudo).parts
                if len(partes) >= 2 and partes[0] in ("src", "app"):
                    modulos_tocados.add(partes[1])
            if len(modulos_tocados) > 2:
                self.aviso(f"{tid}: «Tocar:» abarca múltiples módulos ({', '.join(sorted(modulos_tocados))}); considera dividir la tarea.")

    def _validar_codigo(self):
        """Revisa métricas de código (D37): avisa si hay archivos muy grandes candidatos a refactor."""
        for carpeta in ("src", "app"):
            base = self.raiz / carpeta
            if not base.is_dir():
                continue
            for p in sorted(base.rglob("*.py")):
                if any(part in ("__pycache__", ".pytest_cache", "tests") for part in p.parts):
                    continue
                try:
                    lineas = p.read_bytes().decode("utf-8-sig").splitlines()
                    if len(lineas) > MAX_LINEAS_CODIGO_AVISO:
                        rel = p.relative_to(self.raiz).as_posix()
                        self.aviso(f"{rel} tiene {len(lineas)} líneas (supera {MAX_LINEAS_CODIGO_AVISO} líneas): "
                                   "evaluar en el chat de hito si requiere una tarjeta de refactor REF-NN (D37).")
                except UnicodeDecodeError:
                    pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Revisa que diseño, plan, tarjetas y código sean coherentes.")
    ap.add_argument("--repo", default=".", help="ruta a la raíz del repositorio (por defecto, directorio actual)")
    ap.add_argument("--estricto", action="store_true", help="trata avisos como errores")
    args = ap.parse_args(argv)

    raiz = Path(args.repo).resolve()
    val = Validador(raiz, estricto=args.estricto)
    ret = val.cargar()
    if ret != 0:
        return ret

    errores, avisos = val.validar()

    # Resumen de inventario inspeccionado
    n_tareas = len(val.backlog.tareas) if val.backlog else 0
    n_reb = len(val.backlog.rebanadas) if val.backlog else 0
    n_matriz = len(val.filas_matriz)
    n_rfs = len(val.rfs_diseno)
    n_crits = len(val.criterios_diseno)
    n_tarjetas = len(val.tarjetas)

    print(f"docs/plan/backlog.md: {n_tareas} tareas en {n_reb} rebanadas.")
    print(f"docs/plan/cobertura.md: {n_matriz} filas de cobertura.")
    print(f"docs/requisitos/: {n_rfs} requisitos, {n_crits} criterios de éxito.")
    print(f"docs/plan/tareas/: {n_tarjetas} tarjetas inspeccionadas.\n")

    if errores:
        print(f"Errores ({len(errores)}):")
        for e in errores:
            print(f"  • {e}")
        print()

    if avisos:
        print(f"Avisos ({len(avisos)}):")
        for a in avisos:
            print(f"  • {a}")
        print()

    if errores or (args.estricto and avisos):
        motivo = f"{len(errores)} error(es)" if errores else f"{len(avisos)} aviso(s) tratados como error (--estricto)"
        print(f"Validación fallida: {motivo}. Corrige los problemas antes de continuar.")
        return 1

    print(f"Validación exitosa: diseño, plan, cobertura y tarjetas son coherentes (0 errores, {len(avisos)} avisos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
