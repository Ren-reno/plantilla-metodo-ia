#!/usr/bin/env python3
"""Reparte DISENO.md en docs/ y revisa su formato. Solo usa la biblioteca estándar.

Uso, desde la raíz del repo:
    python tools/init_diseno.py DISENO.md            revisa el formato y reparte el diseño en docs/
    python tools/init_diseno.py DISENO.md --check    solo revisa: no escribe nada y muestra qué repartiría
    python tools/init_diseno.py DISENO.md --force    reparte aunque ya existan los archivos de destino

Qué va a dónde:
    cada "### RF-xxx"                   -> docs/requisitos/RF-xxx-titulo.md
    cada "### ADR-xxxx"                 -> docs/decisiones/xxxx-titulo.md
    datos principales y flujos          -> docs/modelo.md
    el resto de las secciones           -> docs/requisitos/contexto.md
    el original                         -> docs/archivo/ (si estaba en la raíz del repo, se mueve)

Códigos de salida:
    0  todo bien (puede haber avisos)
    1  el formato tiene errores: no se escribió nada
    2  problema de uso o de escritura (archivo no encontrado, destinos ya existentes...)
"""
from __future__ import annotations

import argparse
import difflib
import re
import shutil
import sys
import unicodedata
from collections import namedtuple
from pathlib import Path

# Títulos "##" exactos (los scripts dependen de ellos).
SECCIONES = [
    "Problema y objetivo",
    "Actores",
    "Alcance (dentro / fuera)",
    "Criterios de éxito",
    "Funcionalidades",
    "Datos principales (entidades y relaciones)",
    "Reglas y restricciones",
    "Tecnología (decidida / pendiente)",
    "Decisiones",
    "Preguntas abiertas",
    "Supuestos",
]
FUNCIONALIDADES = "Funcionalidades"
DECISIONES = "Decisiones"
MODELO = "Datos principales (entidades y relaciones)"
FLUJOS = "Flujos principales"
CRITERIOS = "Criterios de éxito"
PREGUNTAS = "Preguntas abiertas"
SUPUESTOS = "Supuestos"
# Todo lo que no es requisito, decisión ni modelo termina en contexto.md.
CONTEXTO = [s for s in SECCIONES if s not in (FUNCIONALIDADES, DECISIONES, MODELO)]
ESTADOS_ADR = ("propuesta", "aceptada", "reemplazada")

Encabezado = namedtuple("Encabezado", "nivel titulo i")

RE_ENCABEZADO = re.compile(r"^(#{1,6})[ \t]+(.*\S)[ \t]*$")
RE_H1 = re.compile(r"^DISENO\s*[—–-]\s*(.+)$")
RE_RF = re.compile(r"^(RF-\d+)\s+·\s+(.+)$")
RE_ADR = re.compile(r"^(ADR-\d{4})\s+·\s+(.+)$")
RE_APORTA = re.compile(r"^Aporta a:\s*([CR]\d+(?:\s*,\s*[CR]\d+)*)\s*$")
RE_ESTADO = re.compile(r"^Estado:\s*(\S+)\s+·\s+Motivo:\s*(.+?)\s+·\s+Afecta:\s*(.+?)\s*$")
RE_PREGUNTA = re.compile(r"^-\s+\*\*(P-\d+)\*\*")
RE_SUPUESTO = re.compile(r"^-\s+\*\*(S-\d+)\*\*")
RE_PENDIENTE = re.compile(r"\[PENDIENTE\s+(P-\d+)\]")
RE_BLOQUEA = re.compile(r"\[BLOQUEA\s+(T-\d+)\]")
RE_RESUELTA = re.compile(r"\[RESUELTA\s*(?:→|->)\s*(ADR-\d{4})\]")
RE_VINETA = re.compile(r"^\s*[-*]\s+\S")


def clasificar(lineas):
    """Marca cada línea: 't' texto, 'c' bloque de código, 'm' comentario HTML.

    Solo las líneas 't' pueden ser títulos o datos del diseño.
    """
    tipos, codigo, comentario = [], False, False
    for texto in lineas:
        s = texto.strip()
        if comentario:
            tipos.append("m")
            if "-->" in s:
                comentario = False
        elif codigo:
            tipos.append("c")
            if s.startswith(("```", "~~~")):
                codigo = False
        elif s.startswith(("```", "~~~")):
            tipos.append("c")
            codigo = True
        elif s.startswith("<!--"):
            tipos.append("m")
            if "-->" not in s[4:]:
                comentario = True
        else:
            tipos.append("t")
    return tipos


def encabezados(lineas, tipos):
    salida = []
    for i, texto in enumerate(lineas):
        if tipos[i] == "t":
            m = RE_ENCABEZADO.match(texto)
            if m:
                salida.append(Encabezado(len(m.group(1)), m.group(2).strip(), i))
    return salida


def slug(texto, maximo=50):
    """'Registrar préstamo (v2)' -> 'registrar-prestamo-v2'."""
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:maximo].rstrip("-") or "sin-titulo"


class Diseno:
    """Lee un DISENO.md, anota errores y avisos con número de línea y sabe repartirlo."""

    def __init__(self, texto):
        self.lineas = texto.splitlines()
        self.tipos = clasificar(self.lineas)
        self.heads = encabezados(self.lineas, self.tipos)
        self.errores = []   # (línea, mensaje); línea 0 = no corresponde a una línea concreta
        self.avisos = []
        self.nombre = "(sin nombre)"
        self.cabecera = []
        self.secciones = {}  # título -> (inicio, fin): índices de línea, fin excluido
        self.criterios = {}
        self.rfs = []        # dicts: id, titulo, ini, fin
        self.adrs = []
        self.preguntas = {}
        self.supuestos = {}

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
    def analizar(self):
        if not any(l.strip() for l in self.lineas):
            self.error(0, "el archivo está vacío")
            return self
        self._titulo()
        self._secciones()
        self._criterios()
        self._funcionalidades()
        self._modelo()
        self._decisiones()
        self._preguntas_y_supuestos()
        self._referencias()
        self._avisos_generales()
        return self

    def _titulo(self):
        h1 = [h for h in self.heads if h.nivel == 1]
        if not h1:
            self.error(0, "falta el título «# DISENO — nombre de la app»")
            return
        primero = h1[0]
        previo = [i for i in range(primero.i) if self.tipos[i] != "m" and self.lineas[i].strip()]
        if previo:
            self.error(previo[0] + 1, "hay texto antes del título «# DISENO — nombre de la app»")
        m = RE_H1.match(primero.titulo)
        if m:
            self.nombre = m.group(1).strip()
        else:
            self.error(primero.i + 1, "el título debe ser «# DISENO — nombre de la app»")
        for extra in h1[1:]:
            self.error(extra.i + 1, "solo puede haber un título «#»; las secciones usan «##»")
        primer_h2 = next((h.i for h in self.heads if h.nivel == 2), len(self.lineas))
        self.cabecera = self._bloque(primero.i + 1, primer_h2)
        while self.cabecera and not self.cabecera[0].strip():
            self.cabecera.pop(0)
        if not any(l.lstrip().startswith(">") for l in self.cabecera):
            self.aviso(primero.i + 1, "falta la línea «> Versión · fecha · fuente…» bajo el título")

    def _secciones(self):
        for h in (x for x in self.heads if x.nivel == 2):
            if h.titulo in SECCIONES:
                if h.titulo in self.secciones:
                    self.error(h.i + 1, f"la sección «{h.titulo}» está repetida "
                                        f"(la primera está en la línea {self.secciones[h.titulo][0] + 1})")
                else:
                    self.secciones[h.titulo] = (h.i, self._fin_seccion(h.i))
            elif re.match(r"^(RF|ADR)-\d+", h.titulo):
                self.error(h.i + 1, f"«## {h.titulo}»: los requisitos y las decisiones van con «###» "
                                    f"dentro de «{FUNCIONALIDADES}» o «{DECISIONES}»")
            else:
                cerca = difflib.get_close_matches(h.titulo, SECCIONES, n=1, cutoff=0.6)
                pista = f"; ¿quisiste decir «{cerca[0]}»?" if cerca else ""
                self.error(h.i + 1, f"sección desconocida «## {h.titulo}»{pista} "
                                    "Los títulos «##» deben ser exactamente los de la plantilla")
        for titulo in SECCIONES:
            if titulo not in self.secciones:
                self.error(0, f"falta la sección «## {titulo}»")

    def _subtitulos(self, ini, fin):
        return [h for h in self.heads if h.nivel == 3 and ini < h.i < fin]

    def _texto_suelto(self, desde, hasta, donde):
        for i in range(desde, hasta):
            if self.tipos[i] != "m" and self.lineas[i].strip():
                self.aviso(i + 1, f"este texto no está dentro de ningún {donde} y no se repartirá "
                                  "a ningún archivo (solo queda en docs/archivo/)")
                return

    def _criterios(self):
        if CRITERIOS not in self.secciones:
            return
        ini, fin = self.secciones[CRITERIOS]
        filas = [(i, self.lineas[i]) for i in range(ini + 1, fin)
                 if self.tipos[i] == "t" and self.lineas[i].lstrip().startswith("|")]
        if not filas:
            self.error(ini + 1, "falta la tabla de criterios: | ID | Criterio | Peso | Fuente (rúbrica / propio) |")
            return

        def celdas(t):
            return [c.strip() for c in t.strip().strip("|").split("|")]

        n0, cab = filas[0]
        c = celdas(cab)
        if len(c) < 4 or [x.lower() for x in c[:3]] != ["id", "criterio", "peso"] \
                or not c[3].lower().startswith("fuente"):
            self.error(n0 + 1, "la cabecera de la tabla debe ser: | ID | Criterio | Peso | Fuente (rúbrica / propio) |")
        datos = filas[1:]
        if datos and re.fullmatch(r"[\s|:\-]+", datos[0][1]):
            datos = datos[1:]
        if not datos:
            self.error(n0 + 1, "la tabla de criterios no tiene ninguna fila")
        for i, t in datos:
            c = celdas(t)
            if len(c) < 4:
                self.error(i + 1, "la fila debe tener 4 columnas: ID, Criterio, Peso y Fuente")
                continue
            cid, texto, peso = c[0], c[1], c[2]
            if not re.fullmatch(r"[CR]\d+", cid):
                self.error(i + 1, f"ID de criterio «{cid}» inválido: usa C1, C2… (R1, R2… si viene de una rúbrica)")
            elif cid in self.criterios:
                self.error(i + 1, f"el criterio {cid} está repetido")
            else:
                self.criterios[cid] = i + 1
            if not texto:
                self.error(i + 1, f"el criterio {cid} no tiene texto")
            try:
                if float(peso.replace(",", ".")) <= 0:
                    raise ValueError
            except ValueError:
                self.error(i + 1, f"el peso «{peso}» del criterio {cid} debe ser un número mayor que 0")

    def _funcionalidades(self):
        if FUNCIONALIDADES not in self.secciones:
            return
        ini, fin = self.secciones[FUNCIONALIDADES]
        subs = self._subtitulos(ini, fin)
        self._texto_suelto(ini + 1, subs[0].i if subs else fin, "requisito")
        if not subs:
            self.error(ini + 1, "no hay ningún requisito: agrega «### RF-001 · Título»")
            return
        for k, h in enumerate(subs):
            fin_b = subs[k + 1].i if k + 1 < len(subs) else fin
            m = RE_RF.match(h.titulo)
            if not m:
                self.error(h.i + 1, f"los requisitos se escriben «### RF-001 · Título» (encontré «### {h.titulo}»)")
                continue
            rid, titulo = m.group(1), m.group(2).strip()
            previo = next((r for r in self.rfs if r["id"] == rid), None)
            if previo:
                self.error(h.i + 1, f"{rid} está repetido (la primera vez está en la línea {previo['ini'] + 1})")
                continue
            sig = h.i + 1
            aporta = []
            ma = RE_APORTA.match(self.lineas[sig].strip()) if sig < fin_b and self.tipos[sig] == "t" else None
            if ma:
                aporta = [x.strip() for x in ma.group(1).split(",")]
            else:
                self.error(h.i + 1, f"{rid}: la línea «Aporta a: C1, C2» debe ir en la línea siguiente al título, "
                                    "sin líneas en blanco entre medio")
            idx = next((i for i in range(h.i + 1, fin_b)
                        if self.tipos[i] == "t" and self.lineas[i].strip() == "Criterios de aceptación:"), None)
            if idx is None:
                self.error(h.i + 1, f"{rid}: falta la línea «Criterios de aceptación:»")
            elif not any(self.tipos[i] == "t" and RE_VINETA.match(self.lineas[i]) for i in range(idx + 1, fin_b)):
                self.error(idx + 1, f"{rid}: no hay criterios de aceptación (líneas que empiezan con «- »)")
            self.rfs.append({"id": rid, "titulo": f"{rid} · {titulo}", "ini": h.i, "fin": fin_b,
                             "aporta": aporta, "texto": titulo})

    def _modelo(self):
        if MODELO not in self.secciones:
            return
        ini, fin = self.secciones[MODELO]
        if not any(h.titulo == FLUJOS for h in self._subtitulos(ini, fin)):
            self.error(ini + 1, f"falta «### {FLUJOS}» dentro de «## {MODELO}»")

    def _decisiones(self):
        if DECISIONES not in self.secciones:
            return
        ini, fin = self.secciones[DECISIONES]
        subs = self._subtitulos(ini, fin)
        self._texto_suelto(ini + 1, subs[0].i if subs else fin, "ADR")
        if not subs:
            self.aviso(ini + 1, "no hay ninguna decisión (ADR); si ya elegiste tecnología, regístrala como ADR")
            return
        for k, h in enumerate(subs):
            fin_b = subs[k + 1].i if k + 1 < len(subs) else fin
            m = RE_ADR.match(h.titulo)
            if not m:
                self.error(h.i + 1, f"las decisiones se escriben «### ADR-0001 · Título» "
                                    f"(encontré «### {h.titulo}»)")
                continue
            aid, titulo = m.group(1), m.group(2).strip()
            previo = next((a for a in self.adrs if a["id"] == aid), None)
            if previo:
                self.error(h.i + 1, f"{aid} está repetido (la primera vez está en la línea {previo['ini'] + 1})")
                continue
            sig = h.i + 1
            me = RE_ESTADO.match(self.lineas[sig].strip()) if sig < fin_b and self.tipos[sig] == "t" else None
            estado = ""
            if not me:
                self.error(h.i + 1, f"{aid}: la línea siguiente al título debe ser "
                                    "«Estado: propuesta · Motivo: … · Afecta: …»")
            elif me.group(1) not in ESTADOS_ADR:
                self.error(sig + 1, f"{aid}: el estado «{me.group(1)}» no es válido; "
                                    f"usa uno de: {', '.join(ESTADOS_ADR)}")
            else:
                estado = me.group(1)
            self.adrs.append({"id": aid, "num": aid[4:], "titulo": f"{aid} · {titulo}", "ini": h.i,
                              "fin": fin_b, "estado": estado, "texto": titulo})

    def _preguntas_y_supuestos(self):
        for seccion, regex, destino, tag in ((PREGUNTAS, RE_PREGUNTA, self.preguntas, "P"),
                                             (SUPUESTOS, RE_SUPUESTO, self.supuestos, "S")):
            if seccion not in self.secciones:
                continue
            ini, fin = self.secciones[seccion]
            for i in range(ini + 1, fin):
                linea = self.lineas[i]
                if self.tipos[i] != "t" or not linea.startswith("- "):
                    continue
                m = regex.match(linea)
                if not m:
                    self.aviso(i + 1, f"esta viñeta no empieza con «- **{tag}-01**» y no se reconoce como "
                                      f"{'pregunta' if tag == 'P' else 'supuesto'}")
                elif m.group(1) in destino:
                    self.error(i + 1, f"{m.group(1)} está repetido")
                else:
                    destino[m.group(1)] = i

    def _referencias(self):
        for rf in self.rfs:
            for c in rf["aporta"]:
                if c not in self.criterios:
                    self.error(rf["ini"] + 1, f"{rf['id']}: «Aporta a» cita {c}, que no está en la tabla de criterios")
        for i, linea in enumerate(self.lineas):
            if self.tipos[i] != "t":
                continue
            for p in RE_PENDIENTE.findall(linea):
                if p not in self.preguntas:
                    self.error(i + 1, f"«[PENDIENTE {p}]» cita una pregunta que no está en «{PREGUNTAS}»")
        adr_ids = {a["id"] for a in self.adrs}
        abiertas = []
        for p, i in self.preguntas.items():
            linea = self.lineas[i]
            resuelta = RE_RESUELTA.search(linea)
            if resuelta and resuelta.group(1) not in adr_ids:
                self.error(i + 1, f"{p}: «[RESUELTA → {resuelta.group(1)}]» cita una decisión que no existe")
            bloquea = RE_BLOQUEA.search(linea)
            if bloquea and not resuelta:
                abiertas.append((p, bloquea.group(1), i))
        if abiertas:
            detalle = ", ".join(f"{p} (bloquea {t})" for p, t, _ in abiertas)
            self.aviso(abiertas[0][2] + 1, f"quedan {len(abiertas)} pregunta(s) abierta(s) que bloquean tareas: {detalle}")

    def _avisos_generales(self):
        propuestas = [a for a in self.adrs if a["estado"] == "propuesta"]
        if propuestas:
            self.aviso(0, f"{len(propuestas)} decisión(es) siguen en estado «propuesta»: acéptalas o "
                          "recházalas en bloque antes de cerrar el diseño")
        sin_llenar = [i for i, l in enumerate(self.lineas) if self.tipos[i] == "t" and ("«" in l or "»" in l)]
        for i in sin_llenar[:5]:
            self.aviso(i + 1, "parece un campo de la plantilla sin llenar: " + self.lineas[i].strip()[:60])
        if len(sin_llenar) > 5:
            self.aviso(0, f"…y {len(sin_llenar) - 5} campo(s) más sin llenar")

    # ---- reparto ----------------------------------------------------------
    def reparto(self):
        """Lista de (ruta relativa, texto) que se escribirían. Solo vale si no hay errores."""
        salida = []
        partes = [f"# Contexto — {self.nombre}", ""]
        if self.cabecera:
            partes += self.cabecera + [""]
        for titulo, (ini, fin) in sorted(self.secciones.items(), key=lambda kv: kv[1][0]):
            if titulo in CONTEXTO:
                partes += self._bloque(ini, fin) + [""]
        salida.append(("docs/requisitos/contexto.md", _unir(partes)))
        for rf in self.rfs:
            b = self._bloque(rf["ini"], rf["fin"])
            b[0] = "# " + rf["titulo"]
            salida.append((f"docs/requisitos/{rf['id']}-{slug(rf['texto'])}.md", _unir(b)))
        ini, fin = self.secciones[MODELO]
        salida.append(("docs/modelo.md", _unir([f"# Modelo — {self.nombre}", ""] + self._bloque(ini, fin))))
        for a in self.adrs:
            b = self._bloque(a["ini"], a["fin"])
            b[0] = "# " + a["titulo"]
            salida.append((f"docs/decisiones/{a['num']}-{slug(a['texto'])}.md", _unir(b)))
        return salida


def _cuenta(n, uno, varios):
    return f"{n} {uno if n == 1 else varios}"


def _unir(lineas):
    return "\n".join(lineas).rstrip("\n") + "\n"


# ---- línea de comandos ----------------------------------------------------
def _mostrar(titulo, items, nombre):
    if not items:
        return
    print(f"{titulo} ({len(items)}):")
    for n, msg in sorted(items, key=lambda x: x[0])[:30]:
        print(f"  {nombre}:{n}: {msg}" if n else f"  {nombre}: {msg}")
    if len(items) > 30:
        print(f"  …y {len(items) - 30} más")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):  # que una consola con otra codificación no tumbe el programa
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="init_diseno.py", description="Reparte DISENO.md en docs/ y revisa su formato.")
    ap.add_argument("archivo", help="ruta del DISENO.md")
    ap.add_argument("--check", action="store_true", help="solo revisa: no escribe nada y muestra qué se repartiría")
    ap.add_argument("--force", action="store_true", help="reparte aunque ya existan los archivos de destino")
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

    d = Diseno(texto).analizar()
    _mostrar("Errores", d.errores, args.archivo)
    _mostrar("Avisos", d.avisos, args.archivo)
    if d.errores:
        print(f"\nEl formato tiene {len(d.errores)} error(es). No se escribió nada. "
              "Corrige el DISENO.md y vuelve a correr el comando.")
        return 1

    reparto = d.reparto()
    archivo_orig = raiz / "docs" / "archivo" / ruta.name
    if ruta.resolve() == archivo_orig.resolve():
        print("Ese archivo ya está en docs/archivo/. Pásame el DISENO.md original.")
        return 2
    destinos = [raiz / rel for rel, _ in reparto] + [archivo_orig]
    existentes = [p for p in destinos if p.exists()]
    print(f"\n{args.archivo}: formato correcto ({_cuenta(len(d.rfs), 'requisito', 'requisitos')}, "
          f"{_cuenta(len(d.adrs), 'decisión', 'decisiones')}, {_cuenta(len(d.criterios), 'criterio', 'criterios')}).")

    if args.check:
        print("\nModo --check: no se escribió nada. Esto es lo que se repartiría:")
        for rel, contenido in reparto:
            print(f"  {rel}  ({len(contenido.splitlines())} líneas)")
        print(f"  docs/archivo/{ruta.name}  (copia del original)")
        if existentes:
            print(f"\nOjo: ya existen {len(existentes)} de esos archivos. Sin --force, el reparto real se negaría.")
        return 0

    if existentes and not args.force:
        print("\nNo se escribió nada porque estos archivos ya existen (usa --force si quieres reemplazarlos):")
        for p in existentes:
            print(f"  {p.relative_to(raiz).as_posix()}")
        return 2

    creados = []
    try:
        for rel, contenido in reparto:
            dest = raiz / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(contenido)
            creados.append(dest)
        archivo_orig.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ruta, archivo_orig)
        creados.append(archivo_orig)
        if archivo_orig.read_bytes() != ruta.read_bytes():
            raise OSError("la copia en docs/archivo/ no coincide con el original")
    except OSError as e:
        for p in creados:
            try:
                p.unlink()
            except OSError:
                pass
        print(f"\nNo pude escribir los archivos ({e}). Deshice lo que alcancé a crear.")
        return 2

    print("\nArchivos creados:")
    for rel, contenido in reparto:
        print(f"  {rel}  ({len(contenido.splitlines())} líneas)")
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
