#!/usr/bin/env python3
"""Cierra una tarea: revisa su reporte, anota banderas, actualiza ESTADO.md y la deja «en revisión» o «hecha».
Solo usa la biblioteca estándar.

Dos momentos, como la recepción provisoria y la definitiva de una obra. Desde la raíz del repo:
    python tools/cerrar.py T-007 reporte.md              provisoria: revisa el reporte y deja la tarea «en revisión»
    python tools/cerrar.py T-007 reporte.md --parcial    parche 1 del modo estricto: la deja «parcial»
    python tools/cerrar.py T-007 reporte.md --reintento  segundo intento tras un fallo
    python tools/cerrar.py T-007 --hecha                 definitiva (el CI salió en verde): «hecha» y borra la tarjeta

Opciones de datos y ensayo:
    --desde REF    commit desde el que mirar lo que cambió la tarea (por defecto HEAD~1: el último commit)
    --commit REF   el commit de la tarea que se anota en ESTADO.md (por defecto HEAD)
    --llm NOMBRE   qué LLM la hizo; se anota en ESTADO.md
    --check        ensayo: revisa y muestra qué haría, sin escribir ni borrar nada

Qué hace al cerrar con reporte:
    - valida el reporte (las 6 secciones, con sus títulos exactos y en orden);
    - mira qué archivos cambió el commit y levanta banderas: archivos fuera de «Tocar:», un documento «solo la
      sección X» cambiado fuera de ella, un archivo de dependencias tocado, cambios en contratos, decisiones que
      afectan a otras tareas;
    - guarda el reporte en docs/plan/reportes/, actualiza docs/plan/ESTADO.md, convierte cada decisión que «Afecta
      a otras tareas» en una propuesta de ADR y regenera el índice docs/decisiones/README.md.
Con --hecha pasa la tarea a «hecha», borra su tarjeta con un borrado normal de archivo (sin «git rm»: tú la
guardas en el commit de cierre junto con ESTADO.md) y lista las tareas que quedan desbloqueadas.

Nunca modifica git: solo lo lee. Todo lo que escribe queda sin commit, para que lo revises con «git diff».

Códigos de salida:
    0  hecho (puede haber banderas y avisos)
    1  el reporte tiene errores o el estado de la tarea no lo permite: no se escribió nada
    2  problema de uso o del entorno (no existe la tarjeta, no hay git, no se pudo escribir)
"""
from __future__ import annotations

import argparse
import difflib
import fnmatch
import re
import sys
from pathlib import Path

import bundle as bd        # lee la tarjeta y habla con git igual que el bundle
import init_diseno as idz  # lector de bloques y formato de salida
import init_plan as ip     # backlog guardado

REL_REPORTES = "docs/plan/reportes"
REL_ESTADO = "docs/plan/ESTADO.md"
REL_DECISIONES = "docs/decisiones"
REL_INDICE = REL_DECISIONES + "/README.md"
DESDE_POR_DEFECTO = "HEAD~1"
SECCIONES = ("Hecho", "Supuestos", "Decisiones tomadas", "Pendientes", "Cómo probar", "Mensaje de commit sugerido")
ESTADOS = ("pendiente", "en curso", "parcial", "en revisión", "bloqueada", "hecha")
FRASE_AFECTA = "Afecta a otras tareas"
SOLO_LECTURA = frozenset({"rev-parse", "diff", "show", "log", "status", "ls-files", "cat-file", "check-ignore"})
DEPENDENCIAS = ("requirements*.txt", "pyproject.toml", "Pipfile", "Pipfile.lock", "poetry.lock", "setup.py",
                "setup.cfg", "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "go.mod", "go.sum",
                "Cargo.toml", "Cargo.lock", "Gemfile", "Gemfile.lock", "composer.json", "composer.lock", "pom.xml",
                "build.gradle", "build.gradle.kts", "mix.exs", "environment.yml")

RE_H1 = re.compile(r"^Reporte\s+((?:T|REF)-\d+)\s*$")
RE_VERIF = re.compile(r"^\s*(?:[-*+]\s+)?\**\s*(no verificado|verificado)\s*\**\s*:", re.IGNORECASE)
RE_VINETA = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")
RE_NINGUNA = re.compile(r"^(?:ninguna|ninguno)\b[\s.]*$", re.IGNORECASE)
RE_COMMIT = re.compile(r"^(?:feat|fix|docs|test|refactor|chore|ci)(?:\([^)]+\))?!?: \S")
RE_MOTIVO = re.compile(r"\s*·\s*Motivo:\s*", re.IGNORECASE)
RE_AFECTA = re.compile(re.escape(FRASE_AFECTA), re.IGNORECASE)
RE_SOLO_SECCION = re.compile(r"solo la secci[oó]n\s+(.+?)\s*$", re.IGNORECASE)
RE_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
RE_ADR_ARCHIVO = re.compile(r"^(\d{4})-(.+)\.md$")
RE_ADR_TITULO = re.compile(r"^#\s+ADR-(\d{4})\s+·\s+(.+?)\s*$")
RE_NOMBRE_BACKLOG = re.compile(r"^#\s+Backlog\s+[—–-]\s+(.+?)\s*$")


# ---- utilidades de texto ---------------------------------------------------------------
def _lista(rutas, maximo=6):
    rutas = list(rutas)
    texto = ", ".join(rutas[:maximo])
    return texto + (f" …y {len(rutas) - maximo} más" if len(rutas) > maximo else "")


def _celda(texto):
    """Un valor para una celda de tabla Markdown: una sola línea, sin «|», «—» si está vacío."""
    t = re.sub(r"\s+", " ", str(texto or "")).replace("|", "/").strip()
    return t or "—"


def _limpiar(texto):
    """Quita los adornos de los bordes de una decisión y el separador « · » (que es el de las líneas de ADR)."""
    t = re.sub(r"\s+", " ", texto).replace("·", "-").strip()
    return t.strip(" .,;:-").strip()


def solo_huecos(texto):
    """¿Esta viñeta de «Decisiones tomadas» es solo campos de la plantilla sin llenar?

    Delega en idz.solo_huecos con la etiqueta propia de una decisión. El límite conocido sigue ahí: una
    decisión escrita íntegra entre comillas no se distingue de un hueco y se descarta, y por eso
    descartarla lleva su propio aviso.
    """
    return idz.solo_huecos(texto, RE_MOTIVO)


def _recortar(texto, maximo):
    if len(texto) <= maximo:
        return texto
    corte = texto[:maximo].rsplit(" ", 1)[0] or texto[:maximo]
    return corte.rstrip(" .,;:-") + "…"


# ---- el reporte ----------------------------------------------------------------------------
class Reporte:
    """Lee un reporte (docs/plantillas/reporte.md): sus 6 secciones, sus decisiones y su mensaje de commit."""

    def __init__(self, texto):
        self.lineas = texto.splitlines()
        self.tipos = idz.clasificar(self.lineas)
        self.heads = idz.encabezados(self.lineas, self.tipos)
        self.errores = []  # (línea, mensaje); línea 0 = no corresponde a una línea concreta
        self.avisos = []
        self.id = None
        self.n_id = 0
        self.secciones = {}     # título -> (inicio del cuerpo, fin): índices de línea, fin excluido
        self.decisiones = []    # dicts: titulo, motivo, afecta
        self.commit = None
        self._analizar()

    def _fin(self, i):
        return next((h.i for h in self.heads if h.i > i and h.nivel <= 2), len(self.lineas))

    def _contenido(self, titulo):
        ini, fin = self.secciones[titulo]
        return [self.lineas[i] for i in range(ini, fin) if self.tipos[i] == "t" and self.lineas[i].strip()]

    def _analizar(self):
        if not any(l.strip() for l in self.lineas):
            self.errores.append((0, "el reporte está vacío"))
            return
        self._titulo()
        self._secciones()
        for titulo in SECCIONES:
            if titulo in self.secciones and not self._contenido(titulo):
                self.errores.append((self.secciones[titulo][0], f"la sección «{titulo}» está vacía"))
        if "Cómo probar" in self.secciones:
            self._como_probar()
        if "Decisiones tomadas" in self.secciones:
            self._decisiones()
        if "Mensaje de commit sugerido" in self.secciones:
            self._commit()
        aviso = idz.aviso_de_huecos(self.lineas, self.tipos)
        if aviso:
            self.avisos.append((0, aviso))

    def _titulo(self):
        h1 = [h for h in self.heads if h.nivel == 1]
        if not h1:
            self.avisos.append((0, "falta el título «# Reporte T-007»"))
            return
        m = RE_H1.match(h1[0].titulo)
        if m:
            self.id, self.n_id = m.group(1), h1[0].i + 1
        elif "«" not in h1[0].titulo:
            self.avisos.append((h1[0].i + 1, "el título debería ser «# Reporte T-007»"))

    def _secciones(self):
        vistos = []  # títulos válidos, en el orden en que aparecen
        for h in (x for x in self.heads if x.nivel == 2):
            if h.titulo not in SECCIONES:
                cerca = difflib.get_close_matches(h.titulo, SECCIONES, n=1, cutoff=0.6)
                pista = f"; ¿quisiste decir «{cerca[0]}»?" if cerca else ""
                self.errores.append((h.i + 1, f"sección desconocida «## {h.titulo}»{pista} Las seis secciones son: "
                                              + " · ".join(SECCIONES)))
            elif h.titulo in self.secciones:
                self.errores.append((h.i + 1, f"la sección «{h.titulo}» está repetida (la primera está en la línea "
                                              f"{self.secciones[h.titulo][0]})"))
            else:
                self.secciones[h.titulo] = (h.i + 1, self._fin(h.i))
                vistos.append(h)
        for titulo in SECCIONES:
            if titulo not in self.secciones:
                self.errores.append((0, f"falta la sección «## {titulo}»"))
        esperado = [t for t in SECCIONES if t in self.secciones]
        if [h.titulo for h in vistos] != esperado:
            primera = next(h for h, t in zip(vistos, esperado) if h.titulo != t)
            self.errores.append((primera.i + 1, "las secciones van en este orden: " + " · ".join(SECCIONES)))

    def _como_probar(self):
        marcas = {m.group(1).lower() for l in self._contenido("Cómo probar") for m in [RE_VERIF.match(l)] if m}
        if "verificado" not in marcas or "no verificado" not in marcas:
            falta = " ni ".join(f"«{x}:»" for x in ("Verificado", "No verificado") if x.lower() not in marcas)
            self.avisos.append((self.secciones["Cómo probar"][0],
                                f"«Cómo probar» no trae {falta}: el reporte debe decir qué comprobaste y qué no"))

    def _decisiones(self):
        lineas = self._contenido("Decisiones tomadas")
        texto = " ".join(l.strip() for l in lineas)
        if not texto or RE_NINGUNA.match(texto):
            return
        grupos, actual = [], None
        for linea in lineas:
            m = RE_VINETA.match(linea)
            if m:
                actual = [m.group(1)]
                grupos.append(actual)
            elif actual is not None and linea[:1] in (" ", "\t"):
                actual.append(linea.strip())  # continuación de la viñeta anterior
        if not grupos:
            grupos = [[texto]]
            self.avisos.append((self.secciones["Decisiones tomadas"][0],
                                "no encontré viñetas en «Decisiones tomadas»: lo traté como una sola decisión"))
        for partes in grupos:
            crudo = " ".join(partes)
            if solo_huecos(crudo):
                # Se descarta, pero se dice: una decisión que desaparece en silencio no llega a ser ADR, y
                # entonces ESTADO.md anuncia que no hay nada que decidir.
                self.avisos.append((self.secciones["Decisiones tomadas"][0],
                                    "descarté una decisión porque solo trae campos de la plantilla sin "
                                    f"llenar: {crudo[:50]}"))
                continue
            afecta = bool(RE_AFECTA.search(crudo))
            partido = RE_MOTIVO.split(RE_AFECTA.sub("", crudo), maxsplit=1)
            titulo = _limpiar(partido[0])
            motivo = _limpiar(partido[1]) if len(partido) > 1 else ""
            if titulo:
                self.decisiones.append({"titulo": titulo, "motivo": motivo, "afecta": afecta})

    def _commit(self):
        lineas = self._contenido("Mensaje de commit sugerido")
        mensaje = lineas[0].strip().strip("`").strip() if lineas else ""
        self.commit = mensaje
        if mensaje and "«" not in mensaje and not RE_COMMIT.match(mensaje):
            self.avisos.append((self.secciones["Mensaje de commit sugerido"][0],
                                f"el mensaje de commit «{mensaje[:50]}» no es un commit convencional "
                                "(feat, fix, docs, test, refactor, chore o ci, seguido de «: descripción»)"))


# ---- git (solo lectura) ----------------------------------------------------------------------
def _git(raiz, *args):
    """Como bundle._git, pero con una lista blanca: este programa nunca modifica git."""
    if not args or args[0] not in SOLO_LECTURA:
        raise bd.GitError(f"cerrar.py nunca modifica git: «{args[0] if args else ''}» no está permitido")
    return bd._git(raiz, *args)


class Cambios:
    """Lo que cambió el trabajo de la tarea: los archivos entre «desde» y HEAD, según git.

    «commit» es el que se anota en ESTADO.md; «propios» son los archivos que ese commit cambió por sí solo,
    y sirven para comprobar que el commit anotado sea de verdad el del trabajo de la tarea.
    """

    def __init__(self, desde, commit, archivos, sucios, propios=()):
        self.desde, self.commit, self.archivos, self.sucios = desde, commit, archivos, sucios
        self.propios = list(propios)


def leer_cambios(raiz, desde, ignorar=(), ref="HEAD"):
    for valor, opcion in ((desde, "--desde"), (ref, "--commit")):
        if valor.startswith("-"):
            raise bd.GitError(f"«{valor}» no es un commit ({opcion} espera un commit, por ejemplo HEAD~2)")
    if _git(raiz, "rev-parse", "--verify", "--quiet", "HEAD^{commit}").returncode != 0:
        raise bd.GitError("este repo todavía no tiene commits: guarda primero el trabajo de la tarea (el bloque de "
                          "comandos del LLM ya hace el commit)")
    if _git(raiz, "rev-parse", "--verify", "--quiet", desde + "^{commit}").returncode != 0:
        pista = (" ¿Es el primer commit del repo? Usa --desde con el commit anterior al trabajo de la tarea."
                 if desde == DESDE_POR_DEFECTO else "")
        raise bd.GitError(f"no encuentro el commit «{desde}».{pista}")
    if ref != "HEAD" and _git(raiz, "rev-parse", "--verify", "--quiet", ref + "^{commit}").returncode != 0:
        raise bd.GitError(f"no encuentro el commit «{ref}» (--commit espera el commit del trabajo de la tarea)")
    corto = _git(raiz, "rev-parse", "--short=7", ref).stdout.strip()
    r = _git(raiz, "diff", "--name-status", "--no-renames", "-z", desde, "HEAD")
    if r.returncode != 0:
        raise bd.GitError("git no pudo comparar los commits: " + (r.stderr.strip() or f"código {r.returncode}"))
    partes = r.stdout.split("\0")
    archivos = [("M" if partes[i][0] == "T" else partes[i][0], partes[i + 1])
                for i in range(0, len(partes) - 1, 2) if partes[i]]
    r = _git(raiz, "status", "--porcelain")
    sucios = [l[3:] for l in r.stdout.splitlines() if r.returncode == 0 and l[3:] not in set(ignorar)]
    # Los archivos del commit anotado, por sí solo: «show» de un merge no los lista, y entonces no se comprueba.
    propios = [f for f in _git(raiz, "show", "--format=", "--name-only", "-z", ref).stdout.split("\0") if f]
    return Cambios(desde, corto, archivos, len(sucios), propios)


def _coincide(ruta, patron):
    """¿Esta ruta cae bajo un elemento de «Tocar:»? El «*» es recursivo; una carpeta incluye lo que cuelga de ella."""
    if "*" in patron:
        return fnmatch.fnmatchcase(ruta, patron)
    return ruta == patron or ruta.startswith(patron.rstrip("/") + "/")


def en_tocar(ruta, items):
    return any(_coincide(ruta, it.ruta) for it in items)


def cambios_fuera_de_seccion(raiz, desde, ruta, seccion):
    """None si la sección no existe en el archivo; si no, los rangos de líneas cambiados fuera de ella."""
    r = _git(raiz, "show", f"HEAD:{ruta}")
    if r.returncode != 0:
        return None
    lineas = r.stdout.splitlines()
    heads = idz.encabezados(lineas, idz.clasificar(lineas))
    objetivo = seccion.strip().strip("«»").strip().lower()
    h = next((x for x in heads if x.titulo.strip().lower() == objetivo), None)
    if h is None:
        return None
    inicio = h.i + 1
    fin = next((x.i for x in heads if x.i > h.i and x.nivel <= h.nivel), len(lineas))
    r = _git(raiz, "diff", "-U0", "--no-renames", desde, "HEAD", "--", ruta)
    fuera = []
    for linea in r.stdout.splitlines():
        m = RE_HUNK.match(linea)
        if not m:
            continue
        primera = int(m.group(1))
        cuantas = 1 if m.group(2) is None else int(m.group(2))
        ultima = primera + max(cuantas, 1) - 1  # una borradura pura (0 líneas) se mide en la línea anterior
        if primera < inicio or ultima > fin:
            fuera.append((primera, ultima))
    return fuera


# ---- ESTADO.md ---------------------------------------------------------------------------------
def fila_nueva():
    return {"estado": "pendiente", "llm": "", "commit": "", "notas": ""}


def leer_estado(texto):
    """(orden, filas) de un ESTADO.md. Lanza ValueError si no se entiende."""
    lineas = texto.splitlines()
    tipos = idz.clasificar(lineas)
    orden, filas, cabecera = [], {}, False
    for i, linea in enumerate(lineas):
        if tipos[i] != "t" or not linea.lstrip().startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if not cabecera:
            if [c.lower() for c in celdas] != ["tarea", "estado", "llm", "commit", "notas"]:
                raise ValueError(f"línea {i + 1}: la cabecera debe ser | Tarea | Estado | LLM | Commit | Notas |")
            cabecera = True
            continue
        if re.fullmatch(r"[\s|:\-]+", linea):
            continue
        if len(celdas) != 5:
            raise ValueError(f"línea {i + 1}: la fila debe tener 5 columnas")
        tid, estado = celdas[0], celdas[1].lower()
        if not bd.RE_ID.match(tid):
            raise ValueError(f"línea {i + 1}: «{tid}» no es una tarea")
        if estado not in ESTADOS:
            raise ValueError(f"línea {i + 1}: el estado «{celdas[1]}» no es válido ({', '.join(ESTADOS)})")
        if tid in filas:
            raise ValueError(f"línea {i + 1}: {tid} está repetida")
        vacio = lambda x: "" if x == "—" else x  # noqa: E731
        filas[tid] = {"estado": estado, "llm": vacio(celdas[2]), "commit": vacio(celdas[3]), "notas": vacio(celdas[4])}
        orden.append(tid)
    if not cabecera:
        raise ValueError("no encuentro la tabla | Tarea | Estado | LLM | Commit | Notas |")
    return orden, filas


def guia_de_estado(m):
    """Tres líneas: en qué etapa está el proyecto, cuál es el siguiente comando y qué espera tu decisión.

    Todo se deriva de lo que ya hay en el repo, así que no añade ningún archivo ni ninguna
    ceremonia. Son tres a propósito: si crecen, esto deja de ser una guía y se convierte en
    otro informe que se desactualiza. Ninguna línea puede contener «|»: las ignora leer_estado.
    """
    tareas = [t for t in m.orden if t.startswith("T-")]
    estado_de = lambda t: m.filas.get(t, {}).get("estado", "pendiente")  # noqa: E731
    del_backlog = m.backlog.tareas if m.backlog is not None else {}
    pendientes = [t for t in tareas if estado_de(t) != "hecha"]

    if not pendientes:
        etapa = "5. Entrega y operación, porque todas las tareas del backlog están hechas"
    else:
        rebs = [del_backlog[t]["reb"] for t in pendientes if del_backlog.get(t, {}).get("reb")]
        total = len(m.backlog.rebanadas) if m.backlog is not None else 0
        etapa = "4. Código" + (f", rebanada {min(rebs)} de {total}" if rebs and total else "")

    en_revision = [t for t in tareas if estado_de(t) == "en revisión"]
    parciales = [t for t in tareas if estado_de(t) == "parcial"]
    if en_revision:
        t = en_revision[0]
        siguiente = (f"mira el CI de {m.filas[t]['commit'] or 'su commit'} y, si está verde, "
                     f"ciérrala con «python tools/cerrar.py {t} --hecha»")
    elif parciales:
        t = parciales[0]
        siguiente = f"falta el parche 2 de {t}: «python tools/bundle.py {t} --parche2»"
    elif not pendientes:
        siguiente = "comprueba la entrega con «python tools/comprobar.py entrega» y publica la versión"
    else:
        libres = [t for t in pendientes if estado_de(t) == "pendiente"
                  and all(estado_de(d) == "hecha" for d in del_backlog.get(t, {}).get("depende", []))]
        con_tarjeta = [t for t in libres if (m.raiz / bd.REL_TAREAS / f"{t}.md").is_file()]
        if con_tarjeta:
            siguiente = f"«python tools/bundle.py {con_tarjeta[0]}»"
        elif libres:
            siguiente = (f"{libres[0]} está desbloqueada pero no tiene tarjeta: escribe las de la ola "
                         "siguiente en el chat de hito")
        else:
            siguiente = "ninguna tarea está desbloqueada: revisa «Depende de:» en docs/plan/backlog.md"

    propuestas = []
    for archivo, (num, _slug) in sorted(adrs_existentes(m.raiz).items()):
        try:
            texto = (m.raiz / REL_DECISIONES / archivo).read_bytes().decode("utf-8-sig")
        except OSError:
            continue
        if leer_adr(texto, num)[2] == "propuesta":
            propuestas.append(f"ADR-{num}")
    decision = ("ninguna" if not propuestas else
                f"{', '.join(propuestas)} siguen en «propuesta»: acéptalas o recházalas, porque "
                "bundle.py se niega con cualquier tarjeta que las cite")

    return [f"- **Etapa:** {etapa}", f"- **Siguiente:** {siguiente}", f"- **Tu decisión:** {decision}"]


def escribir_estado(nombre, orden, filas, guia=()):
    tareas = [t for t in orden if t.startswith("T-")]
    hechas = sum(1 for t in tareas if filas[t]["estado"] == "hecha")
    lineas = [f"# Estado del plan — {nombre}", "",
              "> Generado por `tools/cerrar.py`. No se edita a mano: cualquier cambio se pierde.", "",
              f"Avance: {hechas} de {len(tareas)} {'tarea' if len(tareas) == 1 else 'tareas'} hechas.", ""]
    if guia:
        lineas += list(guia) + [""]
    lineas += ["| Tarea | Estado | LLM | Commit | Notas |", "|---|---|---|---|---|"]
    for tid in orden:
        f = filas[tid]
        lineas.append(f"| {tid} | {f['estado']} | {_celda(f['llm'])} | {_celda(f['commit'])} | {_celda(f['notas'])} |")
    return idz._unir(lineas)


# ---- decisiones (ADR) e índice ---------------------------------------------------------------------
def leer_adr(texto, numero):
    """(número, título, estado) de un ADR."""
    lineas = texto.splitlines()
    tipos = idz.clasificar(lineas)
    titulo, estado = "(sin título)", "(sin estado)"
    for i, linea in enumerate(lineas):
        if tipos[i] != "t":
            continue
        m = RE_ADR_TITULO.match(linea.strip())
        if m and titulo == "(sin título)":
            titulo = m.group(2)
        m = bd.RE_ESTADO_ADR.match(linea)
        if m and estado == "(sin estado)":
            estado = m.group(1).strip().lower() or estado
    return numero, titulo, estado


def adrs_existentes(raiz):
    """{nombre de archivo: (número, slug)} de docs/decisiones/NNNN-slug.md."""
    carpeta = raiz / REL_DECISIONES
    salida = {}
    if carpeta.is_dir():
        for p in sorted(carpeta.glob("*.md")):
            m = RE_ADR_ARCHIVO.match(p.name)
            if m:
                salida[p.name] = (m.group(1), m.group(2))
    return salida


def generar_indice(raiz, nuevos):
    """Texto del índice de decisiones, o None si no hay nada que indexar. «nuevos»: {ruta relativa: texto}."""
    filas = {}
    for nombre, (numero, _) in adrs_existentes(raiz).items():
        texto, _ = bd.leer_archivo(raiz, f"{REL_DECISIONES}/{nombre}")
        filas[nombre] = leer_adr(texto or "", numero)
    for rel, texto in nuevos.items():
        nombre = rel.rsplit("/", 1)[1]
        filas[nombre] = leer_adr(texto, RE_ADR_ARCHIVO.match(nombre).group(1))
    if not filas and not (raiz / REL_INDICE).is_file():
        return None
    lineas = ["# Índice de decisiones", "",
              "> Generado por `tools/cerrar.py` desde los archivos de esta carpeta. No se edita a mano: "
              "cualquier cambio se pierde.", "", "| ADR | Título | Estado |", "|---|---|---|"]
    for nombre in sorted(filas):
        numero, titulo, estado = filas[nombre]
        lineas.append(f"| [ADR-{numero}]({nombre}) | {_celda(titulo)} | {_celda(estado)} |")
    if not filas:
        lineas.append("| — | (todavía no hay decisiones) | — |")
    return idz._unir(lineas)


def proponer_adrs(raiz, tarea, afectan, rel_reporte, avisos):
    """{ruta relativa: texto} de las propuestas de ADR, una por decisión que afecta a otras tareas."""
    existentes = adrs_existentes(raiz)
    siguiente = max([int(n) for n, _ in existentes.values()] + [0]) + 1
    slugs = {s for _, s in existentes.values()}
    salida = {}
    for d in afectan:
        titulo = _recortar(d["titulo"], 90)
        slug = idz.slug(titulo)
        if slug in slugs:
            avisos.append(f"ya existe una decisión llamada «{titulo}»: no la dupliqué como propuesta")
            continue
        slugs.add(slug)
        numero = f"{siguiente:04d}"
        siguiente += 1
        motivo = d["motivo"] or f"se decidió al implementar {tarea} y el reporte no la explica"
        salida[f"{REL_DECISIONES}/{numero}-{slug}.md"] = idz._unir([
            f"# ADR-{numero} · {titulo}", "",
            f"Estado: propuesta · Motivo: {motivo} · Afecta: {tarea} y otras tareas (por precisar)", "",
            "## Contexto", "",
            f"Surgió al implementar {tarea} (reporte: {rel_reporte}). Revisa a qué tareas afecta y acéptala o "
            "recházala: solo tú la pasas a «aceptada»."])
    return salida


# ---- el plan del cierre ----------------------------------------------------------------------------
class Cierre:
    """Todo lo que cerrar.py decidió, sin haber escrito nada todavía."""

    def __init__(self):
        self.codigo = 0
        self.tarea = None
        self.titulo = None
        self.modo = None           # "cierre" | "parcial" | "hecha"
        self.errores = []          # (línea, mensaje) del reporte
        self.negativas = []        # por qué se niega
        self.banderas = []
        self.avisos = []
        self.escrituras = []       # (ruta relativa, texto)
        self.borrar = []           # rutas relativas que se borran
        self.adrs = []             # rutas relativas de las propuestas de ADR
        self.desbloqueadas = []    # (tarea, tiene tarjeta)
        self.commit = None
        self.cambios = None
        self.rel_reporte = None
        self.filas = {}

    def parar(self, codigo, mensaje):
        self.codigo = codigo
        self.negativas.append(mensaje)
        return self


class Mundo:
    """Lo que ya hay en el repo y la tarea necesita saber."""

    def __init__(self, raiz, tarea):
        self.raiz, self.tarea = raiz, tarea
        self.tarjeta = None
        self.backlog = None
        self.nombre = "(sin nombre)"
        self.orden, self.filas = [], {}


def _leer_mundo(raiz, tarea, c, exigir_tarjeta):
    m = Mundo(raiz, tarea)
    rel_tarjeta = f"{bd.REL_TAREAS}/{tarea}.md"
    ruta = raiz / rel_tarjeta
    if ruta.is_file():
        try:
            m.tarjeta = bd.Tarjeta(ruta.read_bytes().decode("utf-8-sig").replace("\r\n", "\n"))
        except UnicodeDecodeError:
            c.parar(1, f"{rel_tarjeta} no está en UTF-8")
            return None
        c.titulo = m.tarjeta.titulo
    elif exigir_tarjeta:
        c.parar(2, f"no existe la tarjeta {rel_tarjeta}. Si la tarea ya está hecha no hay nada que cerrar; si no, "
                   "su ola todavía no se repartió con init_plan.py")
        return None
    else:
        c.avisos.append(f"la tarjeta {rel_tarjeta} ya no existe (¿la borraste a mano?): sigo con el cambio de estado")
    ruta_b = raiz / ip.REL_BACKLOG
    if not ruta_b.is_file():
        c.parar(2, f"no existe {ip.REL_BACKLOG}: cerrar.py lo necesita para armar ESTADO.md. Reparte antes el plan "
                   "con init_plan.py")
        return None
    try:
        texto_b = ruta_b.read_bytes().decode("utf-8-sig")
        m.backlog = ip.leer_backlog_guardado(texto_b)
    except (ValueError, UnicodeDecodeError) as e:
        c.parar(2, f"no pude leer {ip.REL_BACKLOG} ({e})")
        return None
    for linea in texto_b.splitlines():
        nombre = RE_NOMBRE_BACKLOG.match(linea)
        if nombre:
            m.nombre = nombre.group(1)
            break
    if not tarea.startswith("REF-") and tarea not in m.backlog.tareas:
        c.parar(1, f"{tarea} no está en {ip.REL_BACKLOG} (y no es una tarjeta de refactor REF-NN)")
        return None
    viejo_orden, filas = [], {}
    ruta_e = raiz / REL_ESTADO
    if ruta_e.is_file():
        try:
            viejo_orden, filas = leer_estado(ruta_e.read_bytes().decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as e:
            c.parar(2, f"no pude leer {REL_ESTADO} ({e}). Lo escribe solo cerrar.py: si está roto, bórralo y se "
                       "regenera (todas las tareas vuelven a «pendiente»)")
            return None
    m.orden = list(m.backlog.tareas) + [t for t in viejo_orden if t not in m.backlog.tareas]
    if tarea not in m.orden:
        m.orden.append(tarea)
    m.filas = {t: filas.get(t) or fila_nueva() for t in m.orden}
    for t in m.orden:
        if t.startswith("T-") and t not in m.backlog.tareas and "ya no está en el backlog" not in m.filas[t]["notas"]:
            m.filas[t]["notas"] = (m.filas[t]["notas"] + "; " if m.filas[t]["notas"] else "") + "ya no está en el backlog"
    return m


def _evaluar(raiz, tarjeta, es_ref, rep, cambios, reintento, c):
    """Las banderas y avisos que salen de lo que cambió el commit. Devuelve las notas para ESTADO.md."""
    notas = []
    archivos = cambios.archivos
    if not archivos:
        c.avisos.append(f"no hay cambios entre {cambios.desde} y HEAD: ¿hiciste el commit del parche? "
                        "cerrar.py solo mira commits")
    if cambios.sucios:
        c.avisos.append(f"hay {cambios.sucios} archivo(s) con cambios sin guardar: cerrar.py solo mira los commits "
                        f"(desde {cambios.desde})")
    fuera = sorted(r for _, r in archivos if not en_tocar(r, tarjeta.tocar))
    if fuera:
        c.banderas.append(f"archivos fuera de «Tocar:» ({len(fuera)}): {_lista(fuera)}")
        notas.append(f"fuera de Tocar: {len(fuera)}")
    if cambios.propios and tarjeta.tocar and not any(en_tocar(r, tarjeta.tocar) for r in cambios.propios):
        c.avisos.append(f"el commit que voy a anotar ({cambios.commit}) no cambió ningún archivo de «Tocar:»: "
                        "si el trabajo de la tarea está en otro commit, anótalo con «--commit». Un commit "
                        "equivocado en ESTADO.md manda a revisar el CI que no es")
    tests = sorted(r for _, r in archivos if r.startswith("tests/"))
    tests_viejos = sorted(r for e, r in archivos if e in ("M", "D") and r.startswith("tests/"))
    if es_ref and tests:
        c.parar(1, f"una tarjeta de refactor no puede tocar tests (REF-NN solo ordena código): {_lista(tests)}")
    elif tests_viejos and reintento:
        c.parar(1, f"con --reintento, un test que ya existía no puede cambiar: {_lista(tests_viejos)}. "
                   "Corrige el código, no los tests")
    elif tests_viejos:
        c.avisos.append(f"cambiaron tests que ya existían: {_lista(tests_viejos)}. Con --reintento esto sería un error")
        notas.append(f"tests modificados: {len(tests_viejos)}")
    deps = sorted(r for _, r in archivos if any(fnmatch.fnmatchcase(r.rsplit("/", 1)[-1], p) for p in DEPENDENCIAS))
    if deps:
        pista = ("" if rep.decisiones else " «Decisiones tomadas» no dice nada: la regla 5 pide declarar las "
                                          "dependencias nuevas ahí")
        c.banderas.append(f"archivo de dependencias tocado: {_lista(deps)}.{pista}")
        notas.append("dependencias")
    contratos = sorted(r for _, r in archivos if r.startswith(("docs/contratos/", "contratos/")))
    if contratos:
        c.banderas.append(f"cambios en contratos: {_lista(contratos)}")
        notas.append("contratos")
    for estado, ruta in archivos:
        if estado == "D":
            continue
        for it in tarjeta.tocar:
            if not it.nota or not _coincide(ruta, it.ruta):
                continue
            solo = RE_SOLO_SECCION.search(it.nota)
            if solo and ruta.endswith(".md") and estado == "M":
                fuera_sec = cambios_fuera_de_seccion(raiz, cambios.desde, ruta, solo.group(1))
                if fuera_sec is None:
                    c.avisos.append(f"no encontré la sección «{solo.group(1)}» en {ruta}: no pude comprobar que el "
                                    "cambio quede dentro de ella")
                elif fuera_sec:
                    rangos = ", ".join(f"{a}-{b}" if a != b else str(a) for a, b in fuera_sec)
                    c.banderas.append(f"{ruta} cambió fuera de la sección «{solo.group(1)}» (líneas {rangos})")
                    notas.append("cambio fuera de sección")
            elif it.nota.lower().startswith("solo"):
                c.avisos.append(f"revisa a mano {ruta}: la tarjeta dice «{it.nota}» y no sé comprobarlo "
                                "(solo sé hacerlo en documentos Markdown)")
    return notas


def _planear_cierre(m, c, reporte, nombre_reporte, mover, parcial, reintento, desde, llm, commit=None):
    raiz, tarea, tarjeta = m.raiz, m.tarea, m.tarjeta
    rep = Reporte(reporte)
    c.errores += rep.errores
    c.avisos += [f"{nombre_reporte}:{n}: {msg}" if n else f"{nombre_reporte}: {msg}" for n, msg in rep.avisos]
    if rep.id and rep.id != tarea:
        c.errores.append((rep.n_id, f"el reporte es de {rep.id}, pero estás cerrando {tarea}"))
    if c.errores:
        c.codigo = 1
        return c
    if tarjeta.errores:
        return c.parar(1, f"la tarjeta {bd.REL_TAREAS}/{tarea}.md tiene errores (" + "; ".join(x for _, x in tarjeta.errores[:3]) + ")")
    if parcial and tarjeta.modo != "estricto":
        c.parar(1, "--parcial solo sirve con una tarjeta de «Modo: estricto»; esta no lo es")
    actual = m.filas[tarea]["estado"]
    if actual == "hecha":
        c.parar(1, f"{tarea} ya está «hecha»")
    elif actual == "en revisión" and not reintento:
        c.parar(1, f"{tarea} ya está «en revisión». Si es un segundo intento (por ejemplo, el CI falló y lo "
                   "corregiste), usa --reintento")
    elif actual == "parcial" and parcial and not reintento:
        c.parar(1, f"{tarea} ya está «parcial». Si es un segundo intento del parche 1, usa --reintento; si es el "
                   "parche 2, no uses --parcial")
    c.rel_reporte = f"{REL_REPORTES}/{tarea}{'-parche1' if parcial else ''}.md"
    if (raiz / c.rel_reporte).exists() and not reintento:
        c.parar(1, f"ya existe {c.rel_reporte}: si es un segundo intento, usa --reintento")
    if c.negativas:
        c.codigo = 1
        return c
    try:
        cambios = leer_cambios(raiz, desde or DESDE_POR_DEFECTO, ignorar=[mover] if mover else [],
                               ref=commit or "HEAD")
    except bd.GitError as e:
        return c.parar(2, str(e))
    c.cambios, c.commit = cambios, cambios.commit
    notas = _evaluar(raiz, tarjeta, tarea.startswith("REF-"), rep, cambios, reintento, c)
    afectan = [d for d in rep.decisiones if d["afecta"]]
    for d in afectan:
        c.banderas.append(f"decisión que afecta a otras tareas: {_recortar(d['titulo'], 70)} (se propone como ADR)")
    if afectan:
        notas.append(f"decisiones que afectan a otras tareas: {len(afectan)}")
    if parcial:
        notas.insert(0, "parche 1 de 2")
    if c.negativas:
        c.codigo = 1
        return c
    propuestas = proponer_adrs(raiz, tarea, afectan, c.rel_reporte, c.avisos)
    c.adrs = sorted(propuestas)
    fila = m.filas[tarea]
    if not llm and not fila["llm"]:
        c.avisos.append("no declaraste quién hizo la tarea: la columna LLM de ESTADO.md queda vacía, y una celda "
                        "vacía no dice que no hubo LLM, dice que nadie lo anotó. Pásalo con «--llm nombre» "
                        "(o «--llm ninguno» si la hiciste a mano)")
    fila["estado"] = "parcial" if parcial else "en revisión"
    fila["commit"] = cambios.commit
    fila["notas"] = "; ".join(notas)
    if llm:
        fila["llm"] = llm
    c.modo = "parcial" if parcial else "cierre"
    c.filas = m.filas
    c.escrituras.append((c.rel_reporte, "\n".join(reporte.splitlines()).rstrip("\n") + "\n"))
    c.escrituras += sorted(propuestas.items())
    indice = generar_indice(raiz, propuestas)
    if indice is not None:
        c.escrituras.append((REL_INDICE, indice))
    c.escrituras.append((REL_ESTADO, escribir_estado(m.nombre, m.orden, m.filas, guia_de_estado(m))))
    if mover:
        c.borrar.append(mover)
    return c


def _planear_hecha(m, c):
    raiz, tarea = m.raiz, m.tarea
    actual = m.filas[tarea]["estado"]
    if actual != "en revisión":
        consejo = {"pendiente": f"primero ciérrala con su reporte (cerrar.py {tarea} reporte.md)",
                   "parcial": f"falta el parche 2 (bundle.py {tarea} --parche2) y cerrarlo con su reporte",
                   "hecha": "ya está hecha"}.get(actual, "solo una tarea «en revisión» puede pasar a «hecha»")
        return c.parar(1, f"{tarea} está «{actual}»: {consejo}")
    m.filas[tarea]["estado"] = "hecha"
    c.commit = m.filas[tarea]["commit"]
    c.filas = m.filas
    c.modo = "hecha"
    if m.tarjeta is not None:
        c.borrar.append(f"{bd.REL_TAREAS}/{tarea}.md")
    for tid, t in m.backlog.tareas.items():
        if tarea in t["depende"] and m.filas[tid]["estado"] == "pendiente" \
                and all(m.filas.get(d, {}).get("estado") == "hecha" for d in t["depende"]):
            c.desbloqueadas.append((tid, (raiz / bd.REL_TAREAS / f"{tid}.md").is_file()))
    indice = generar_indice(raiz, {})
    actual_indice = (raiz / REL_INDICE).read_bytes().decode("utf-8-sig") if (raiz / REL_INDICE).is_file() else None
    if indice is not None and indice != actual_indice:
        c.escrituras.append((REL_INDICE, indice))
    c.escrituras.append((REL_ESTADO, escribir_estado(m.nombre, m.orden, m.filas, guia_de_estado(m))))
    return c


def planear(raiz, tarea, reporte=None, nombre_reporte="reporte.md", mover=None, hecha=False, parcial=False,
            reintento=False, desde=None, llm=None, commit=None):
    """Decide qué escribir y qué borrar. No toca el disco: devuelve un Cierre."""
    c = Cierre()
    tarea = (tarea or "").strip().upper()
    c.tarea = tarea
    if not bd.RE_ID.match(tarea):
        return c.parar(2, f"«{tarea}» no es el número de una tarea (usa T-007 o REF-01)")
    m = _leer_mundo(raiz, tarea, c, exigir_tarjeta=not hecha)
    if m is None:
        return c
    if hecha:
        return _planear_hecha(m, c)
    return _planear_cierre(m, c, reporte, nombre_reporte, mover, parcial, reintento, desde, llm, commit)


# ---- escritura -----------------------------------------------------------------------------------------
def _aplicar(raiz, escrituras, borrar):
    """Escribe y borra todo o nada: si algo falla, deja los archivos como estaban."""
    previos, nuevos = {}, []
    try:
        for rel, texto in escrituras:
            dest = raiz / rel
            if dest.is_file():
                previos[dest] = dest.read_bytes()
            else:
                nuevos.append(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(texto)
        for rel in borrar:
            ruta = raiz / rel
            if ruta.is_file():
                previos[ruta] = ruta.read_bytes()
                ruta.unlink()  # borrado normal del sistema de archivos: no toca el índice de git
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


# ---- línea de comandos ------------------------------------------------------------------------------------
def _imprimir_motivos(c, nombre_reporte):
    if c.errores:
        idz._mostrar("Errores", c.errores, nombre_reporte)
    if c.negativas or c.errores:
        print(f"\nNo se cerró {c.tarea}. Motivos:")
        for motivo in c.negativas:
            print(f"  - {motivo}")
        if c.errores:
            print(f"  - El reporte tiene {len(c.errores)} error(es): corrígelo y vuelve a correr el comando.")
        if c.avisos:
            print("\nAvisos:")
            for a in c.avisos:
                print(f"  - {a}")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):  # que una consola con otra codificación no tumbe el programa
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="cerrar.py", description="Cierra una tarea: revisa su reporte, actualiza "
                                 "ESTADO.md y la deja «en revisión» o «hecha».")
    ap.add_argument("tarea", help="número de la tarea, por ejemplo T-007 (o REF-01)")
    ap.add_argument("reporte", nargs="?", help="el reporte que entregó el LLM (por ejemplo reporte.md)")
    ap.add_argument("--hecha", action="store_true",
                    help="recepción definitiva: el CI salió en verde; la tarea queda hecha y se borra su tarjeta")
    ap.add_argument("--parcial", action="store_true", help="parche 1 del modo estricto: la tarea queda «parcial»")
    ap.add_argument("--reintento", action="store_true", help="segundo intento de la tarea tras un fallo")
    ap.add_argument("--desde", metavar="REF", help=f"commit desde el que mirar los cambios (por defecto {DESDE_POR_DEFECTO})")
    ap.add_argument("--commit", metavar="REF",
                    help="el commit de la tarea que se anota en ESTADO.md (por defecto HEAD)")
    ap.add_argument("--llm", metavar="NOMBRE", help="qué LLM hizo la tarea (se anota en ESTADO.md)")
    ap.add_argument("--check", action="store_true", help="ensayo: no escribe ni borra nada")
    args = ap.parse_args(argv)
    if args.hecha:
        if args.reporte or args.parcial or args.reintento or args.desde or args.llm or args.commit:
            ap.error("--hecha se usa solo: cerrar.py T-007 --hecha")
    elif not args.reporte:
        ap.error("falta el reporte: cerrar.py T-007 reporte.md")

    raiz = Path(__file__).resolve().parent.parent
    texto, ruta, mover = None, None, None
    if args.reporte:
        ruta = Path(args.reporte)
        if not ruta.is_file():
            print(f"No encuentro el reporte «{args.reporte}». Corre el comando desde la raíz del repo y revisa el nombre.")
            return 2
        try:
            texto = ruta.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
        except UnicodeDecodeError:
            print(f"{args.reporte}: el archivo no está en UTF-8. Guárdalo como UTF-8 y vuelve a intentar.")
            return 1
        if ruta.resolve().parent == (raiz / REL_REPORTES).resolve():
            print("Ese reporte ya está en docs/plan/reportes/. Pásame el original.")
            return 2
        if ruta.resolve().parent == raiz:
            mover = ruta.name

    c = planear(raiz, args.tarea, texto, args.reporte or "", mover, args.hecha, args.parcial, args.reintento,
                args.desde, args.llm, args.commit)
    if c.negativas or c.errores:
        _imprimir_motivos(c, args.reporte or "")
        return c.codigo or 1

    if c.modo == "hecha":
        print(f"{c.tarea} · {c.titulo or '(tarjeta ya borrada)'}: recepción definitiva. Pasa a «hecha».")
    else:
        print(f"Reporte de {c.tarea} · {c.titulo}: revisado. La tarea queda «{c.filas[c.tarea]['estado']}».")
        resumen = {e: sum(1 for x, _ in c.cambios.archivos if x == e) for e in "AMD"}
        print(f"Commit {c.commit}; archivos desde {c.cambios.desde}: {len(c.cambios.archivos)} "
              f"({resumen['A']} nuevos, {resumen['M']} modificados, {resumen['D']} borrados)")
    if c.banderas:
        print(f"\nBanderas, para revisar ({len(c.banderas)}):")
        for b in c.banderas:
            print(f"  - {b}")
    if c.avisos:
        print(f"\nAvisos ({len(c.avisos)}):")
        for a in c.avisos:
            print(f"  - {a}")
    if c.adrs:
        print("\nPropuestas de ADR (estado «propuesta»: acéptalas o recházalas):")
        for a in c.adrs:
            print(f"  - {a}")

    if args.check:
        print("\nModo --check: no se escribió ni se borró nada. Esto se escribiría:")
        for rel, texto_rel in c.escrituras:
            print(f"  {rel}  ({len(texto_rel.splitlines())} líneas){'  (reemplaza el actual)' if (raiz / rel).exists() else ''}")
        for rel in c.borrar:
            print(f"  se borraría {rel}")
        return 0
    try:
        _aplicar(raiz, c.escrituras, c.borrar)
    except OSError as e:
        print(f"\nNo pude escribir los archivos ({e}). Dejé todo como estaba.")
        return 2

    print("\nEscribió:")
    for rel, texto_rel in c.escrituras:
        print(f"  {rel}")
    for rel in c.borrar:
        print(f"  borró {rel}" + ("  (el reporte se movió desde la raíz del repo)" if rel == mover else ""))
    if c.modo == "hecha":
        if c.desbloqueadas:
            print("\nTareas desbloqueadas:")
            for tid, con_tarjeta in c.desbloqueadas:
                print(f"  - {tid}: " + (f"lista; arma su bundle con «python tools/bundle.py {tid}»"
                                        if con_tarjeta else "todavía sin tarjeta (su ola aún no se escribió)"))
        else:
            print("\nNo quedó ninguna tarea desbloqueada por esta.")
        print("\nSiguiente paso: guarda el cierre con un commit (ESTADO.md y la tarjeta borrada van juntos).")
    elif c.modo == "parcial":
        print(f"\nParche 1 del modo estricto: antes de seguir, confirma que el rojo es el correcto.")
        print("  correcto:   falla por falta de funcionalidad (un «no implementado» o una aserción que no se cumple)")
        print("  incorrecto: ImportError, ModuleNotFoundError, SyntaxError o NameError: el test ni siquiera pudo correr")
        print(f"Siguiente paso: arma el bundle del parche 2 con «python tools/bundle.py {c.tarea} --parche2».")
    else:
        print("\nSiguiente paso: revisa con «git diff» y acepta o rechaza las propuestas de ADR. Cuando el CI de "
              f"GitHub salga en verde: «python tools/cerrar.py {c.tarea} --hecha».")
    return 0


if __name__ == "__main__":
    sys.exit(main())
