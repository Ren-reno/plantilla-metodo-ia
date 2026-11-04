#!/usr/bin/env python3
"""Aplica un parche (.patch) al repo actual con una cadena de seguridad. Solo usa la biblioteca estándar.

Uso, desde la raíz del repo (o desde cualquiera de sus carpetas):
    python tools/aplicar.py                         aplica el .patch más reciente de tu carpeta de parches
    python tools/aplicar.py T-007-registrar.patch   aplica ese archivo (un nombre suelto se busca también
                                                    en tu carpeta de parches)
    python tools/aplicar.py --check                 ensayo: limpia y prueba la cadena, sin aplicar nada
    python tools/aplicar.py T-007-tests.patch --estricto "pytest tests/actividades"
                                                    modo estricto, parche 1 (D40): aplica, corre el test y
                                                    comprueba que falle por la razón correcta

La carpeta de parches sale de ~/.metodo-ia.json (clave «carpeta_parches», la misma que lee bundle.py). Si el
archivo no existe, usa ~/Downloads y, si no hay, ~/Descargas.

Qué hace (D4, D18, D38, D40, D45):
    1. Busca la raíz del repo y corre git siempre ahí: desde una subcarpeta, «git apply» devuelve 0 y no
       aplica nada de lo que está fuera de ella.
    2. Limpia el parche en una copia temporal; el archivo original no se toca: quita las vallas de markdown
       (columna 0), el texto que no es del parche, el BOM y el UTF-16; convierte CRLF a LF cuando también los
       encabezados lo traen (con CRLF en todo el parche, «--ignore-whitespace» deja un \\r pegado a cada línea
       nueva) y agrega el salto de línea final (sin él, git dice «corrupt patch» incluso con --recount).
    3. Cadena de D18, acumulativa: «git apply --check» simple; si falla, con --recount; si falla, con
       --recount --ignore-whitespace. El primer paso que pasa se aplica con las mismas banderas.
    4. Si ninguno pasa, diagnostica SIN tocar tu repo: dice si el parche ya estaba aplicado y, si no, corre
       «git apply --reject» sobre una copia temporal de los archivos que toca el parche. Muestra, por cada
       bloque que no encaja, las 3 líneas que esperaba el parche y las 3 que tiene el archivo, listas para
       pegar al LLM («solo ese bloque corregido»).
    5. Con --estricto, tras aplicar corre el comando de test y mira qué excepción lo hizo fallar (no el código
       de salida: un NameError sale con 1, igual que un rojo correcto). Rojo correcto: NotImplementedError o
       una aserción que no se cumple. Incorrecto: SyntaxError, ImportError, ModuleNotFoundError, NameError.

Nunca guarda nada en git (D45): ni índice, ni commits, ni stash. Solo usa «git apply» (sin --index ni
--cached), «git rev-parse --show-toplevel» y «git status --short»; el resto lo hace el bloque de comandos.
Lo único que cambia en tu repo son los archivos del parche. Los archivos de texto se leen con UTF-8
(utf-8-sig donde puede haber BOM) y se escriben con UTF-8 y newline="\\n".

Códigos de salida:
    0  el parche se aplicó (o, con --check, se puede aplicar); con --estricto, además el rojo es el correcto
    1  el parche no se puede aplicar (aunque se limpie) o, con --estricto, el rojo no es el correcto
    2  problema de uso o de entorno: no hay git, esto no es un repo, no hay parche, carpeta inexistente
"""
import argparse
import contextlib
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import namedtuple
from pathlib import Path

# ---- constantes ----------------------------------------------------------------------------------------
NOMBRE_CONFIG = ".metodo-ia.json"
CLAVE_CARPETA = "carpeta_parches"
CARPETAS_POR_DEFECTO = ("Downloads", "Descargas")
ANTIGUEDAD_AVISO_S = 3600  # provisional: un parche con más de 1 hora probablemente no es el que acabas de pedir
LINEAS_SALIDA_TEST = 40
ANCHO_MAXIMO_LINEA = 110

# La cadena de D18. Es acumulativa: cada paso suma una bandera a las del anterior.
PASOS = (
    ("simple", ()),
    ("--recount", ("--recount",)),
    ("--recount --ignore-whitespace", ("--recount", "--ignore-whitespace")),
)
BANDERAS_TOLERANTES = ("--recount", "--ignore-whitespace")

# D45: lista blanca de lo que este programa puede ejecutar en git. «--reject» solo sobre una copia temporal.
PERMITIDOS = {
    "rev-parse": {"--show-toplevel"},
    "status": {"--short"},
    "apply": {"--check", "--recount", "--ignore-whitespace", "--reverse", "--numstat", "-z", "--reject"},
}

# Vallas de markdown: solo cuentan en la columna 0. Una línea de contexto de un .md es « ```powershell»
# (con un espacio delante) y un parche nunca puede tener una línea que empiece con ` o ~.
RE_VALLA = re.compile(r"^(?:`{3,}|~{3,})\s*[\w.+#-]*\s*$")
RE_DIFF_GIT = re.compile(r"^diff --git ")
RE_BLOQUE = re.compile(r"^(@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@)")
RE_ORIGEN = re.compile(r"^(?:rename|copy) from (.+)\n(?:rename|copy) to (.+)$", re.MULTILINE)
# Git informa «at line N» o «at ruta:N»; la ruta puede incluir espacios y dos puntos.
RE_CORRUPTO = re.compile(r"corrupt patch at (?:line |[^\r\n]+:)(\d+)[ \t]*\r?$", re.MULTILINE)
RE_RUTA_INVALIDA = re.compile(r"^error: invalid path '(.+)'\s*$", re.MULTILINE)
RE_BLOQUE_BIEN = re.compile(r"^Hunk #\d+ applied cleanly\.", re.MULTILINE)
RE_ARCHIVO_BIEN = re.compile(r"^Applied patch .+ cleanly\.", re.MULTILINE)
RE_YA_EXISTE = re.compile(r"^error: (.+): already exists in working directory\s*$", re.MULTILINE)
RE_NO_EXISTE = re.compile(r"^error: (.+): No such file or directory\s*$", re.MULTILINE)
PREFIJOS_PARCHE = ("diff --git ", "index ", "--- ", "+++ ", "@@ ", "new file mode ", "deleted file mode ",
                   "old mode ", "new mode ", "similarity index ", "dissimilarity index ", "rename from ",
                   "rename to ", "copy from ", "copy to ", "Binary files ", "GIT binary patch", "literal ",
                   "delta ")

# Modo estricto (D40). Solo Python (pytest y unittest); para otro stack se amplían estas listas.
# Prefijos con los que pytest y unittest escriben una excepción: «E   X», «ruta:3: X» (--tb=line) y el
# resumen «FAILED ruta::test - X».
_PREFIJO_EXC = r"^(?:E\s+|\S+:\d+:\s+|(?:FAILED|ERROR)\s.*?\s-\s+)?(?:\w+\.)*"
EXCEPCIONES_MALAS = ("SyntaxError", "IndentationError", "TabError", "ImportError", "ModuleNotFoundError",
                     "NameError", "UnboundLocalError")
EXCEPCIONES_BUENAS = ("NotImplementedError", "AssertionError")
RE_ROJO_MALO = re.compile(_PREFIJO_EXC + "(" + "|".join(EXCEPCIONES_MALAS) + r")\b", re.MULTILINE)
RE_ROJO_BUENO = re.compile(_PREFIJO_EXC + "(" + "|".join(EXCEPCIONES_BUENAS) + r")\b", re.MULTILINE)
# pytest reescribe «assert a == b» y no escribe la palabra AssertionError: «E   assert (1 + 1) == 3».
RE_ASERCION_PYTEST = re.compile(r"^E\s+assert\b|^(?:FAILED|ERROR)\s.*?\s-\s+assert\b|^E\s+Failed: DID NOT RAISE",
                                re.MULTILINE)
RE_SIN_TESTS = re.compile(r"no tests ran|^Ran 0 tests|collected 0 items|NO TESTS RAN", re.MULTILINE | re.IGNORECASE)

Limpieza = namedtuple("Limpieza", "texto notas")


class ErrorUso(Exception):
    """Algo del entorno o de cómo se usó el programa (código 2)."""


class ErrorParche(Exception):
    """El parche no sirve ni limpiándolo (código 1)."""


class GitError(Exception):
    """git no se pudo ejecutar, o se pidió algo que este programa nunca hace (código 2)."""


# ---- git (lista blanca) --------------------------------------------------------------------------------
def _git(cwd, *args, en_copia=False):
    """Corre git en «cwd». Lista blanca (D45): este programa nunca guarda nada en git.

    «--reject» solo se acepta con en_copia=True: la copia temporal vive fuera del repo y git no la toma por
    parte de ningún repo (GIT_CEILING_DIRECTORIES; sin eso, dentro de un repo git dice «Skipped patch» y sale 0).
    Los mensajes de git se piden en inglés: no se interpreta su texto salvo unos pocos mensajes conocidos.
    """
    if not args or args[0] not in PERMITIDOS:
        raise GitError(f"aplicar.py nunca guarda nada en git: «{args[0] if args else ''}» no está permitido")
    for a in args[1:]:
        if a.startswith("-") and a not in PERMITIDOS[args[0]]:
            raise GitError(f"aplicar.py nunca guarda nada en git: la opción «{a}» de «git {args[0]}» no está permitida")
    if "--reject" in args and not en_copia:
        raise GitError("«--reject» solo se permite sobre una copia temporal, nunca en tu repo")
    env = dict(os.environ, LC_ALL="C", LANGUAGE="C")
    if en_copia:
        env["GIT_CEILING_DIRECTORIES"] = str(Path(cwd).parent)
    try:
        return subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=str(cwd), env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as e:
        raise GitError(f"no pude correr git ({e}). Instálalo y corre el comando desde tu repo")


def raiz_del_repo(cwd):
    r = _git(cwd, "rev-parse", "--show-toplevel")
    if r.returncode != 0 or not r.stdout.strip():
        raise ErrorUso("esta carpeta no está dentro de un repo de git. Abre la terminal en la carpeta de tu app "
                       "(confírmalo con pwd) y vuelve a correr el comando")
    return Path(r.stdout.strip())


def cambios_sin_guardar(raiz, excluir=None):
    """Cuántos archivos tiene el repo con cambios sin guardar (sin contar el propio parche si vive en el repo)."""
    r = _git(raiz, "status", "--short")
    if r.returncode != 0:
        return 0
    n = 0
    for linea in r.stdout.splitlines():
        if not linea.strip():
            continue
        if excluir is not None and linea.startswith("?? ") and linea[3:].strip().strip('"') == excluir:
            continue
        n += 1
    return n


# ---- elegir el parche ----------------------------------------------------------------------------------
def _carpeta_personal(home):
    try:
        return Path(home) if home is not None else Path.home()
    except RuntimeError:
        raise ErrorUso("no pude ubicar tu carpeta personal para leer ~/.metodo-ia.json")


def _expandir(valor, base):
    valor = os.path.expandvars(valor)
    if valor == "~":
        return base
    if valor.startswith(("~/", "~\\")):
        return base / valor[2:]
    return Path(valor)


def leer_carpeta_parches(home=None):
    """(carpeta, avisos): la carpeta de parches según ~/.metodo-ia.json o, sin configurar, la de descargas."""
    base = _carpeta_personal(home)
    ruta = base / NOMBRE_CONFIG
    avisos, valor = [], None
    if ruta.is_file():
        try:
            crudo = json.loads(ruta.read_bytes().decode("utf-8-sig"))  # utf-8-sig: PowerShell suele guardar con BOM
            if not isinstance(crudo, dict):
                raise ValueError("no es un objeto JSON")
            v = crudo.get(CLAVE_CARPETA)
            if isinstance(v, str) and v.strip():
                valor = v.strip()
        except (ValueError, UnicodeDecodeError) as e:
            avisos.append(f"no pude leer {ruta} ({e}); uso la carpeta de descargas por defecto")
    if valor is not None:
        carpeta = _expandir(valor, base)
        if not carpeta.is_dir():
            raise ErrorUso(f"la carpeta de parches que dice {ruta} no existe: {carpeta}")
        return carpeta, avisos
    for nombre in CARPETAS_POR_DEFECTO:
        if (base / nombre).is_dir():
            return base / nombre, avisos
    raise ErrorUso("no encuentro tu carpeta de parches: no hay «" + CLAVE_CARPETA + "» en ~/" + NOMBRE_CONFIG
                   + " ni una carpeta " + " o ".join(CARPETAS_POR_DEFECTO) + " en " + str(base)
                   + ". Pasa el parche como argumento (python tools/aplicar.py ruta/al.patch) o configura la carpeta"
                   " (ver tools/README.md)")


def parche_mas_reciente(carpeta):
    """(parche o None, avisos): el .patch con la fecha de modificación más reciente de la carpeta."""
    try:
        entradas = list(Path(carpeta).iterdir())
    except OSError as e:
        raise ErrorUso(f"no pude leer la carpeta de parches {carpeta} ({e})")
    parches, con_txt = [], []
    for p in entradas:
        try:
            if not p.is_file():
                continue
            fecha = p.stat().st_mtime
        except OSError:
            continue
        nombre = p.name.lower()
        if nombre.endswith(".patch"):
            parches.append((fecha, p.name, p))
        elif nombre.endswith(".patch.txt"):
            con_txt.append((fecha, p.name, p))
    elegido = max(parches, key=lambda t: (t[0], t[1]))[2] if parches else None
    avisos = []
    if con_txt:
        fecha_txt, nombre_txt, _ = max(con_txt, key=lambda t: (t[0], t[1]))
        if elegido is None or fecha_txt > elegido.stat().st_mtime:
            avisos.append(f"hay un «{nombre_txt}» más nuevo: el Bloc de notas le agregó «.txt». Renómbralo a .patch "
                          "(al guardar, elige «Todos los archivos») y vuelve a correr el comando")
    return elegido, avisos


def resolver_parche(arg, home=None):
    """(ruta, avisos): el parche que se va a aplicar."""
    if arg:
        p = Path(os.path.expanduser(arg))
        if p.is_file():
            return p, []
        if p.is_dir():
            raise ErrorUso(f"«{arg}» es una carpeta, no un parche")
        if len(p.parts) == 1:  # un nombre suelto: también se busca en la carpeta de parches
            try:
                carpeta, _ = leer_carpeta_parches(home)
            except ErrorUso:
                carpeta = None
            if carpeta is not None and (carpeta / arg).is_file():
                return carpeta / arg, []
        raise ErrorUso(f"no encuentro el parche «{arg}»")
    carpeta, avisos = leer_carpeta_parches(home)
    elegido, extra = parche_mas_reciente(carpeta)
    if elegido is None:
        raise ErrorUso(f"no hay ningún archivo .patch en {carpeta}" + ("; " + extra[0] if extra else ""))
    return elegido, avisos + extra


def _hace(segundos):
    s = max(0, int(segundos))
    if s < 60:
        return "hace menos de 1 min"
    if s < 3600:
        return f"hace {s // 60} min"
    if s < 86400:
        return f"hace {s // 3600} h {s % 3600 // 60} min"
    return f"hace {s // 86400} d"


def _kb(n_bytes):
    return f"{n_bytes / 1024:.1f} KB"


# ---- leer y limpiar el parche -------------------------------------------------------------------------
def decodificar(datos):
    """(texto, notas). Acepta UTF-8 con o sin BOM y UTF-16 con BOM (lo que deja «>» en Windows PowerShell 5.1)."""
    notas = []
    try:
        if datos.startswith((b"\xff\xfe", b"\xfe\xff")):
            texto = datos.decode("utf-16")
            notas.append("estaba en UTF-16; lo leí igual")
        elif datos.startswith(b"\xef\xbb\xbf"):
            texto = datos.decode("utf-8-sig")
            notas.append("quité el BOM del inicio")
        else:
            texto = datos.decode("utf-8")
    except UnicodeDecodeError:
        raise ErrorParche("el parche no está en UTF-8. Guárdalo de nuevo: Bloc de notas, «Guardar como», "
                          "Codificación «UTF-8» (D45)")
    if "\x00" in texto:
        raise ErrorParche("el archivo trae bytes nulos: parece UTF-16 sin BOM o un binario, no un parche. "
                          "Guárdalo de nuevo como UTF-8")
    return texto, notas


def leer_parche(ruta):
    try:
        datos = Path(ruta).read_bytes()
    except OSError as e:
        raise ErrorUso(f"no pude leer {ruta} ({e})")
    return decodificar(datos)


def _es_diff(lineas):
    return any(RE_DIFF_GIT.match(l) or RE_BLOQUE.match(l) for l in lineas)


def _es_linea_de_parche(l):
    return l == "" or l[0] in " +-\\" or l.startswith(PREFIJOS_PARCHE)


def _recortar(lineas):
    """Quita el texto que sobra antes del primer encabezado y el texto suelto que queda al final."""
    ini = 0
    for i, l in enumerate(lineas):
        if RE_DIFF_GIT.match(l) or (l.startswith("--- ") and i + 1 < len(lineas) and lineas[i + 1].startswith("+++ ")):
            ini = i
            break
    fin = len(lineas)
    if not any(l.startswith("GIT binary patch") for l in lineas[ini:]):  # sus datos en base85 parecen texto
        j, prosa = fin, False
        while j > ini:
            l = lineas[j - 1]
            if l == "":
                j -= 1
            elif _es_linea_de_parche(l):
                break
            else:
                prosa = True
                j -= 1
        if prosa:
            # se deja a lo más una línea vacía: puede ser un contexto en blanco al que el editor le quitó el espacio
            fin = j + 1 if (j < len(lineas) and lineas[j] == "") else j
    return lineas[ini:fin]


def limpiar(texto):
    """Limpieza(texto, notas): el parche sin vallas ni texto ajeno, con LF y con salto de línea final."""
    if not texto.strip():
        raise ErrorParche("el archivo del parche está vacío")
    notas = []
    lineas = texto.split("\n")  # no splitlines(): cortaría en \x0c, \u2028 y otros que pueden estar en el código
    termina_con_salto = lineas[-1] == ""
    if termina_con_salto:
        lineas.pop()

    # CRLF en todo el parche: lo guardó así un editor. Si solo trae CRLF el contenido, es un parche legítimo
    # para un archivo CRLF y se deja como está.
    cabeceras = [l for l in lineas if l.startswith(("diff --git ", "@@ "))]
    if cabeceras and all(l.endswith("\r") for l in cabeceras):
        lineas = [l[:-1] if l.endswith("\r") else l for l in lineas]
        notas.append("convertí los finales de línea de CRLF a LF")

    n_vallas = sum(1 for l in lineas if RE_VALLA.match(l))
    descartadas = 0
    if n_vallas:
        # Lo que hay entre vallas se conserva solo si es un diff (se descartan el reporte, los comandos y la
        # prosa); así también sirve si falta la valla de apertura o la de cierre.
        bloques, actual = [], []
        for l in lineas:
            if RE_VALLA.match(l):
                bloques.append(actual)
                actual = []
            else:
                actual.append(l)
        bloques.append(actual)
        elegidos = []
        for b in bloques:
            if _es_diff(b):
                elegidos.append(b)
            else:
                descartadas += sum(1 for l in b if l.strip())
        notas.insert(0, f"quité {n_vallas} {'línea' if n_vallas == 1 else 'líneas'} de vallas de markdown")
    else:
        elegidos = [lineas] if _es_diff(lineas) else []

    resultado = []
    for b in elegidos:
        recortado = _recortar(b)
        descartadas += sum(1 for l in b if l.strip()) - sum(1 for l in recortado if l.strip())
        resultado.extend(recortado)
    if not resultado:
        raise ErrorParche("no encuentro un parche en el archivo: busco líneas que empiecen con «diff --git» o con "
                          "«@@ -a,b +c,d @@». Si guardaste otra cosa (¿el reporte?), guarda solo el bloque del parche")
    if descartadas:
        notas.append(f"descarté {descartadas} {'línea' if descartadas == 1 else 'líneas'} de texto que no era del parche")
    ultima = lineas[-1] if lineas else None
    if not termina_con_salto and resultado[-1] == ultima and not RE_VALLA.match(ultima):
        notas.append("agregué el salto de línea final que faltaba")
    return Limpieza("\n".join(resultado) + "\n", notas)


@contextlib.contextmanager
def _parche_temporal(texto):
    """El parche limpio en un archivo temporal (UTF-8, sin BOM, con \\n); se borra al salir."""
    fd, ruta = tempfile.mkstemp(prefix="aplicar-", suffix=".patch")
    os.close(fd)
    try:
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        yield ruta
    finally:
        try:
            os.remove(ruta)
        except OSError:
            pass


# ---- la cadena de seguridad ----------------------------------------------------------------------------
def probar_cadena(raiz, ruta_parche):
    """((nombre, banderas) o None, intentos): el primer paso de D18 cuyo «--check» pasa.

    intentos = [(nombre, código, stderr)] de todos los pasos probados.
    """
    intentos = []
    for nombre, banderas in PASOS:
        r = _git(raiz, "apply", "--check", *banderas, ruta_parche)
        intentos.append((nombre, r.returncode, r.stderr))
        if r.returncode == 0:
            return (nombre, banderas), intentos
    return None, intentos


def archivos_del_parche(raiz, ruta_parche, texto=""):
    """[(ruta, añadidas, borradas, origen)] según «git apply --numstat -z».

    git solo da el nombre final; el origen de un renombre o de una copia sale de las líneas «rename from» /
    «copy from» del propio parche (texto).
    """
    r = _git(raiz, "apply", "--numstat", "-z", ruta_parche)
    if r.returncode != 0:
        return []
    origenes = {destino: origen for origen, destino in RE_ORIGEN.findall(texto)}
    salida = []
    for parte in r.stdout.split("\0"):
        campos = parte.split("\t", 2)
        if len(campos) == 3 and campos[2]:
            salida.append((campos[2], campos[0], campos[1], origenes.get(campos[2])))
    return salida


# ---- diagnóstico: sin tocar el repo --------------------------------------------------------------------
Bloque = namedtuple("Bloque", "encabezado inicio lineas")


def _esperadas(bloque):
    """Las líneas que el parche espera encontrar: el contexto y las que borra."""
    return [l[1:] for l in bloque.lineas if l[:1] in (" ", "-")]


@contextlib.contextmanager
def _copia_temporal(raiz, archivos):
    """Una carpeta temporal con copia de los archivos que ya existen y toca el parche. Se borra al salir."""
    carpeta = Path(tempfile.mkdtemp(prefix="aplicar-copia-"))
    try:
        base, destino_base = Path(raiz).resolve(), carpeta.resolve()
        for ruta, _ins, _borr, origen in archivos:
            for nombre in (ruta, origen):
                if not nombre:
                    continue
                try:
                    fuente = (base / nombre).resolve()
                    fuente.relative_to(base)  # nunca se copia nada de fuera del repo
                    destino = (carpeta / nombre).resolve()
                    destino.relative_to(destino_base)  # ni se escribe fuera de la copia
                except (ValueError, OSError):
                    continue
                if fuente.is_file():
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(str(fuente), str(destino))
        yield carpeta
    finally:
        shutil.rmtree(str(carpeta), ignore_errors=True)


def _leer_texto(ruta):
    with open(str(ruta), encoding="utf-8", errors="replace", newline="") as f:
        return f.read()


def leer_rechazos(carpeta):
    """{ruta: [Bloque]} a partir de los .rej que dejó «git apply --reject» en la copia."""
    salida = {}
    for rej in sorted(Path(carpeta).rglob("*.rej")):
        ruta = rej.relative_to(carpeta).as_posix()[:-len(".rej")]
        lineas = _leer_texto(rej).split("\n")
        if lineas and lineas[-1] == "":
            lineas.pop()
        bloques, actual = [], None
        for l in lineas:
            l = l.rstrip("\r")
            m = RE_BLOQUE.match(l)
            if m:
                actual = Bloque(m.group(1), int(m.group(2)), [])
                bloques.append(actual)
            elif actual is not None:
                if l[:1] in (" ", "+", "-"):
                    actual.lineas.append(l)
                elif l == "":
                    actual.lineas.append(" ")  # contexto en blanco al que el editor le quitó el espacio
        salida[ruta] = bloques
    return salida


def localizar_desajuste(esperadas, reales, inicio):
    """Dónde deja de encajar un bloque. Devuelve (k, pos, solo_espacios), con índices desde 0.

    k = primera línea esperada que no encaja; pos = dónde la esperaba el parche, dentro del archivo.
    Se compara sin los espacios del final de línea; si así todo coincide, la diferencia es de espacios o de
    finales de línea y solo_espacios vale True.
    """
    ne = [l.rstrip() for l in esperadas]
    nr = [l.rstrip() for l in reales]
    coincidencias = [b for b in difflib.SequenceMatcher(None, ne, nr, autojunk=False).get_matching_blocks()
                     if b.size > 0]
    minimo = min(2, len(ne))  # una línea suelta (típicamente en blanco) coincide en cualquier parte
    solidas = [b for b in coincidencias if b.size >= minimo] or coincidencias
    if not solidas:
        return 0, max(0, min(inicio - 1, len(reales))), False
    i0, j0, n0 = solidas[0]
    if i0 > 0:
        return 0, max(0, j0 - i0), False
    if n0 >= len(ne):
        return 0, j0, True
    return n0, j0 + n0, False


def _recortar_linea(l):
    return l if len(l) <= ANCHO_MAXIMO_LINEA else l[:ANCHO_MAXIMO_LINEA - 3] + "..."


def _mostrar_lineas(lineas, crudas=False):
    if not lineas:
        return ["      (el archivo termina antes de esa línea)"]
    return ["      | " + _recortar_linea(repr(l) if crudas else l.rstrip("\r")) for l in lineas]


def explicar_bloque(raiz, ruta, bloque):
    """Líneas de texto: las 3 líneas que esperaba el parche frente a las 3 que tiene el archivo."""
    try:
        reales = _leer_texto(Path(raiz) / ruta).split("\n")
        if reales and reales[-1] == "":
            reales.pop()
    except OSError:
        return [f"  {bloque.encabezado}: no pude leer {ruta} para compararlo"]
    esperadas = _esperadas(bloque)
    if not esperadas:
        return [f"  {bloque.encabezado}: solo agrega líneas y no encuentra dónde (el contexto no existe en el archivo)"]
    k, pos, solo_espacios = localizar_desajuste(esperadas, reales, bloque.inicio)
    salida = [f"  {bloque.encabezado}  (desde la línea {pos + 1} del archivo)"]
    if solo_espacios:
        salida.append("    Las líneas se ven iguales: la diferencia está en espacios, tabuladores o finales de línea "
                      "(o en dónde termina el archivo). Así las ve git:")
    salida.append("    El parche esperaba:")
    salida += _mostrar_lineas(esperadas[k:k + 3], solo_espacios)
    salida.append("    El archivo tiene:")
    salida += _mostrar_lineas(reales[pos:pos + 3], solo_espacios)
    return salida


def _lineas_cercanas(texto, n_linea):
    """Las 3 líneas del parche alrededor de la línea n (desde 1), con una marca en la que dice git."""
    lineas = texto.split("\n")
    salida = []
    for i in range(max(1, n_linea - 1), min(len(lineas), n_linea + 1) + 1):
        marca = ">" if i == n_linea else " "
        salida.append(f"    {marca} {i:>4} | {_recortar_linea(lineas[i - 1].rstrip(chr(13)))}")
    return salida


def diagnosticar(raiz, texto, ruta_parche, intentos):
    """(líneas, pegar_al_llm): por qué no aplica. No cambia nada en el repo: usa una copia temporal.

    pegar_al_llm es False cuando no hay nada que corregir en el parche (ya estaba aplicado).
    """
    # 1) ¿ya está aplicado? Es la causa más probable cuando se elige solo el parche más reciente.
    if _git(raiz, "apply", "--check", "--reverse", *BANDERAS_TOLERANTES, ruta_parche).returncode == 0:
        return (["Este parche ya está aplicado: su reverso encaja en tu repo, así que no hay nada que corregir. "
                 "Si no lo esperabas, mira si abriste el parche anterior (¿hay uno más nuevo en tu carpeta de "
                 "parches? Pásalo como argumento)."], False)

    salida = []
    # 2) parche dañado
    ultimo = intentos[-1][2] if intentos else ""
    m = RE_CORRUPTO.search(ultimo)
    if m:
        n = int(m.group(1))
        salida += [f"El parche está dañado cerca de la línea {n} (git dice «corrupt patch»). Casi siempre es el conteo "
                   "de líneas de un «@@» que no cuadra (--recount ya se probó) o un parche cortado al copiarlo.",
                   "  Las líneas (la marca > es la que señala git):"]
        salida += _lineas_cercanas(texto, n)
        return salida, True

    # 3) ruta que git no acepta (sale del repo, o es absoluta): el LLM se equivocó de ruta
    m = RE_RUTA_INVALIDA.search(ultimo)
    if m:
        return ([f"El parche usa la ruta «{m.group(1)}», que sale del repo o no es válida, y git no la permite. Pide "
                 "al LLM que use solo rutas dentro del repo, relativas a su raíz."], True)

    # 4) copia temporal + --reject: sirve para ver todos los bloques que no encajan sin dejar nada en el repo
    archivos = archivos_del_parche(raiz, ruta_parche, texto)
    with _copia_temporal(raiz, archivos) as copia:
        r = _git(copia, "apply", "--reject", *BANDERAS_TOLERANTES, ruta_parche, en_copia=True)
        rechazos = leer_rechazos(copia)
    for nombre in sorted(set(RE_NO_EXISTE.findall(r.stderr))):
        salida.append(f"El parche modifica «{nombre}», que no existe en tu repo: el LLM inventó la ruta o falta un "
                      "parche anterior.")
    for nombre in sorted(set(RE_YA_EXISTE.findall(r.stderr))):
        salida.append(f"El parche crea «{nombre}», pero ya existe en tu repo.")
    origen_de = {ruta: origen for ruta, _ins, _borr, origen in archivos if origen}
    for ruta, bloques in rechazos.items():
        real = origen_de.get(ruta, ruta)  # en un renombre, lo que hay que comparar es el archivo de origen
        n = len(bloques)
        titulo = ruta if real == ruta else f"{ruta} (antes: {real})"
        salida.append(f"{titulo}: {n} {'bloque no encaja' if n == 1 else 'bloques no encajan'} con lo que tiene tu "
                      "archivo (¿lo cambiaste después de armar el bundle?).")
        for b in bloques:
            salida += explicar_bloque(raiz, real, b)
    if salida and (RE_BLOQUE_BIEN.search(r.stderr) or RE_ARCHIVO_BIEN.search(r.stderr)):
        salida.append("El resto del parche sí encaja y no hay que corregirlo.")
    if not salida:
        detalle = [l for l in r.stderr.splitlines() if l.strip()][:8]
        salida.append("git no dio más detalles. Esto fue lo que dijo:")
        salida += ["  " + l for l in detalle] or ["  (nada)"]
    return salida, True


# ---- modo estricto (D40) -------------------------------------------------------------------------------
def correr_prueba(comando, raiz):
    """(código, salida) del comando de test, corrido en la raíz del repo con la salida unida (stdout y stderr)."""
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    try:
        r = subprocess.run(comando, shell=True, cwd=str(raiz), env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    except OSError as e:
        raise ErrorUso(f"no pude correr el comando de test «{comando}» ({e})")
    return r.returncode, r.stdout


def clasificar_rojo(codigo, salida):
    """(veredicto, detalle) con veredicto en «correcto», «incorrecto», «paso» o «indeterminado».

    Lee la excepción, no el código de salida: pytest sale con 2 si no pudo importar y con 1 si falló un test,
    pero un NameError en un test también sale con 1; unittest sale con 1 en los dos casos.
    Si aparecen marcas buenas y malas a la vez, gana la mala.
    """
    if codigo == 0:
        return "paso", ""
    malas = sorted({m.group(1) for m in RE_ROJO_MALO.finditer(salida)})
    if malas:
        return "incorrecto", ", ".join(malas)
    buenas = sorted({m.group(1) for m in RE_ROJO_BUENO.finditer(salida)})
    if "AssertionError" not in buenas and RE_ASERCION_PYTEST.search(salida):
        buenas.append("una aserción que no se cumple")
    if buenas:
        return "correcto", " y ".join(buenas)
    if codigo == 5 or RE_SIN_TESTS.search(salida):
        return "indeterminado", "el comando no ejecutó ningún test (¿la ruta o el nombre del test es otro?)"
    return "indeterminado", ("no vi NotImplementedError ni una aserción, ni errores de importación o de sintaxis "
                             f"(el comando salió con {codigo})")


def _mostrar_cola(salida):
    lineas = salida.splitlines()
    if len(lineas) > LINEAS_SALIDA_TEST:
        print(f"  (... {len(lineas) - LINEAS_SALIDA_TEST} líneas más arriba)")
        lineas = lineas[-LINEAS_SALIDA_TEST:]
    for l in lineas:
        print("  " + l)


def _modo_estricto(raiz, comando):
    print(f"\nModo estricto (D40): corriendo «{comando}» ...")
    codigo, salida = correr_prueba(comando, raiz)
    _mostrar_cola(salida)
    veredicto, detalle = clasificar_rojo(codigo, salida)
    if veredicto == "correcto":
        print(f"\nRojo CORRECTO: el test falla por {detalle}, que es lo esperado en el parche 1.")
        print("Si el mensaje de arriba te convence, pega el segundo bloque (el commit «test: ...»).")
        return 0
    if veredicto == "incorrecto":
        print(f"\nRojo INCORRECTO: el test falla por {detalle}, no por falta de funcionalidad.")
        print("El parche quedó aplicado sin guardar (D38). Pega la salida de arriba al LLM y pídele el parche 1 "
              "corregido a partir de este estado, o descarta el intento con «git stash -u».")
        return 1
    if veredicto == "paso":
        print("\nLos tests PASARON. En el parche 1 del modo estricto se espera un rojo: un test que no puede fallar "
              "no prueba nada.")
        print("Revisa que los tests prueben algo y que el esqueleto no implemente ya la lógica. El parche quedó "
              "aplicado sin guardar.")
        return 1
    print(f"\nNo pude confirmar la razón del rojo: {detalle}.")
    print("Léelo tú: si es NotImplementedError o una aserción que no se cumple, sigue con el segundo bloque; si no, "
          "pega la salida al LLM. El parche quedó aplicado sin guardar.")
    return 1


# ---- el comando ----------------------------------------------------------------------------------------
def _informar_fallo(raiz, nombre, texto, tmp, intentos):
    pasos = ", ".join(n for n, _c, _e in intentos)
    print(f"\nNo pude aplicar «{nombre}» (probé: {pasos}).")
    print("Tu repo no cambió.\n")
    lineas, pegar_al_llm = diagnosticar(raiz, texto, tmp, intentos)
    print("Qué pasó:")
    for l in lineas:
        print("  " + l if not l.startswith(" ") else l)
    if pegar_al_llm:
        print("\nQué hacer: pega al LLM lo de «Qué pasó» con este texto (docs/COMO-TRABAJAR.md, «Un parche falló»):")
        print("  Al aplicar el parche me salió este error: (lo de «Qué pasó»). Devuélveme solo la parte corregida "
              "(el archivo y el bloque @@ que falló), no el parche entero.")
    return 1


def _ejecutar(parche_arg, estricto, solo_check, cwd, home, avisos):
    raiz = raiz_del_repo(cwd)
    ruta, extra = resolver_parche(parche_arg, home)
    avisos.extend(extra)
    try:
        info = ruta.stat()
        edad = time.time() - info.st_mtime
        try:
            carpeta = ruta.resolve().parent
        except OSError:
            carpeta = ruta.parent
        print(f"Parche: {ruta.name}  ({_kb(info.st_size)}, {_hace(edad)}; carpeta: {carpeta})")
        if edad > ANTIGUEDAD_AVISO_S:
            avisos.append(f"el parche tiene más de 1 hora ({_hace(edad)}): ¿es el que acabas de pedir al LLM? "
                          "Si no, guarda el nuevo o pásalo como argumento")
    except OSError:
        print(f"Parche: {ruta.name}")
    texto, notas = leer_parche(ruta)
    limpio = limpiar(texto)
    notas.extend(limpio.notas)
    if notas:
        print("Limpieza: " + "; ".join(notas) + ".")
    try:
        dentro_del_repo = ruta.resolve().relative_to(Path(raiz).resolve()).as_posix()
    except (ValueError, OSError):
        dentro_del_repo = None
    sucios = cambios_sin_guardar(raiz, dentro_del_repo)
    if sucios:
        avisos.append(f"tu repo ya tiene {sucios} {'archivo' if sucios == 1 else 'archivos'} con cambios sin guardar "
                      "(es lo esperado si estás reintentando tras un test fallido; si no, míralo con «git status --short»)")

    with _parche_temporal(limpio.texto) as tmp:
        paso, intentos = probar_cadena(raiz, tmp)
        if paso is None:
            return _informar_fallo(raiz, ruta.name, limpio.texto, tmp, intentos)
        nombre_paso, banderas = paso
        if nombre_paso == "simple":
            print("Cadena de seguridad: pasó el «git apply --check» simple.")
        else:
            print(f"Cadena de seguridad: pasó con «{nombre_paso}» (los pasos anteriores no pasaron).")
        if "--ignore-whitespace" in banderas:
            avisos.append("se aplicó con --ignore-whitespace: git perdonó diferencias de espacios o de finales de "
                          "línea. Revisa con «git diff» que no quedaron finales de línea mezclados")
        archivos = archivos_del_parche(raiz, tmp, limpio.texto)
        resumen = [f"  {r}  +{i} -{b}" + (f"  (antes: {o})" if o else "") for r, i, b, o in archivos]
        if solo_check:
            print(f"\nEnsayo (--check): el parche se puede aplicar; no se aplicó nada ({len(archivos)} "
                  f"{'archivo' if len(archivos) == 1 else 'archivos'}):")
            print("\n".join(resumen))
            if estricto:
                print("Con --check no se corre el comando de test.")
            return 0
        r = _git(raiz, "apply", *banderas, tmp)
        if r.returncode != 0:  # no debería pasar: el --check con las mismas banderas ya pasó
            print("\ngit apply falló aunque el --check había pasado. Esto fue lo que dijo:")
            print("  " + (r.stderr.strip().replace("\n", "\n  ") or "(nada)"))
            return 1
    print(f"\nAplicado ({len(archivos)} {'archivo' if len(archivos) == 1 else 'archivos'}):")
    print("\n".join(resumen))
    print("Nada se guardó en git (ni índice ni commits): eso lo hace el resto de tu bloque de comandos.")
    if estricto:
        return _modo_estricto(raiz, estricto)
    return 0


def ejecutar(parche_arg=None, estricto=None, solo_check=False, cwd=None, home=None):
    """Corre el flujo completo y devuelve el código de salida (0, 1 o 2). Imprime lo que hace."""
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    avisos = []
    try:
        codigo = _ejecutar(parche_arg, estricto, solo_check, cwd, home, avisos)
    except (ErrorUso, GitError) as e:
        print(f"Error: {e}.")
        codigo = 2
    except ErrorParche as e:
        print(f"\nNo pude usar el parche: {e}.")
        codigo = 1
    if avisos:
        print(f"\nAvisos ({len(avisos)}):")
        for a in avisos:
            print(f"  - {a}")
    return codigo


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):  # que una consola con otra codificación no tumbe el programa
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        prog="aplicar.py",
        description="Aplica un parche al repo actual: lo limpia, prueba la cadena de seguridad de git apply y, si "
                    "falla, dice exactamente qué no encaja. Nunca guarda nada en git.")
    ap.add_argument("parche", nargs="?",
                    help="archivo .patch (por defecto, el más reciente de tu carpeta de parches)")
    ap.add_argument("--check", action="store_true", dest="solo_check",
                    help="ensayo: limpia el parche y prueba la cadena, sin aplicar nada")
    ap.add_argument("--estricto", metavar="COMANDO",
                    help="modo estricto, parche 1 (D40): tras aplicar corre COMANDO (el test de la tarjeta) y "
                         "comprueba que falle por NotImplementedError o una aserción, no por un error de "
                         "importación o de sintaxis")
    args = ap.parse_args(argv)
    if args.estricto is not None and not args.estricto.strip():
        ap.error("--estricto necesita el comando de test, por ejemplo --estricto \"pytest tests/actividades\"")
    return ejecutar(args.parche, args.estricto, args.solo_check)


if __name__ == "__main__":
    sys.exit(main())
