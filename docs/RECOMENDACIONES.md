# Recomendaciones Técnicas y Estratégicas para `plantilla-metodo-ia`

> **Diagnóstico general:** El sistema diseñado en la **Memoria v4** es conceptualmente sólido, tiene fundamentos teóricos de primer nivel (*Harness Engineering*, *Spec-Driven Development* adaptado, rebanadas verticales de Kent Beck y Birgitta Böckeler) y resuelve de manera brillante el ahorro de tokens en planes gratuitos.
>
> Para llevarlo del papel a la práctica sin tropiezos, a continuación se presentan las recomendaciones organizadas por **prioridad de impacto**.

---

## 1. Prioridad Inmediata: Reducción de Fricción en el Flujo Diario

### 1.1 Construir `aplicar.py` antes de cualquier otra herramienta
* **Por qué:** Hoy el usuario depende de copiar el parche, guardarlo en el Bloc de notas con UTF-8, abrir PowerShell y ejecutar `git apply`. En Windows, cualquier salto de línea CRLF/LF o espacio extra puede provocar un error críptico de `corrupt patch`.
* **Propuesta:** `aplicar.py` debe ser un script de un solo comando (`python tools/aplicar.py`) que:
  1. Detecte automáticamente el último archivo `.patch` en `Downloads/`.
  2. Limpie bloques markdown si el usuario pegó el diff con vallas ````diff`.
  3. Ejecute automáticamente la cadena de seguridad acordada (`--check`, `--recount`, `--ignore-whitespace`).
  4. Si falla, muestre exactamente las 3 líneas que no encajaron para pedir la corrección al LLM.

### 1.2 Reparar la guarda del bloque de comandos en PowerShell
* **El riesgo:** En la sección 11.6 de la memoria se identificó un riesgo crítico: si se pega un bloque de comandos en PowerShell:
  ```powershell
  git apply archivo.patch
  pytest tests/modulo/       # <-- SI ESTE TEST FALLA...
  git add -A
  git commit -m "feat: ..."  # <-- POWERSHELL SIGUE Y HACE COMMIT IGUAL
  ```
* **Solución recomendada:** Condicionar el commit al resultado del test mediante `$LASTEXITCODE`:
  ```powershell
  git apply "$env:USERPROFILE\Downloads\T-007.patch"
  pytest tests/modulo/
  if ($LASTEXITCODE -eq 0) {
      git add -A
      git commit -m "feat: registrar actividad"
      git push
  } else {
      Write-Error "Tests en fallo: commit cancelado. Revisa la salida antes de continuar."
  }
  ```

---

## 2. Recomendaciones Metodológicas: Evitar la "Parálisis por Análisis"

### 2.1 Construir una app piloto pequeña YA (Validación Empírica)
* **Situación:** El Nivel 2 (D34 a D37) tiene un diseño elegante (caminos proporcionales, plan por olas, modo estricto, chat de hito), pero todo está marcado como **(no probado)**.
* **Recomendación:** No esperes a tener construidas todas las herramientas (`validar.py`, `cerrar.py`, `bundle.py`) para probar el método en una app real.
  - Elige una app deliberadamente pequeña (ejemplo: un CLI de seguimiento de hábitos o una API REST simple en SQLite).
  - Haz la etapa 1 (`DISENO.md`), córtala con `init_diseno.py` y programa 2 o 3 rebanadas aplicando el flujo de olas a mano.
  - Esto revelará si los formatos de las tarjetas son demasiado rígidos o si falta algún campo antes de pasar semanas programando scripts de validación.

### 2.2 `validar.py` debe construirse en fases (v0.1 → v1.0)
* **El riesgo:** La lista de chequeos planificada para `validar.py` tiene más de 12 validaciones cruzadas (matriz de cobertura, grafos de dependencias, ciclos, verificación de diagramas PlantUML, etc.). Intentar programarlo todo de golpe puede atascar el avance.
* **Propuesta incremental:**
  - **Fase 1 (Esencial):** Validar que ningún RF quede huérfano, que las tarjetas tengan `Fuera de alcance` y que no excedan 4 criterios de aceptación.
  - **Fase 2 (Avanzada):** Validar la matriz calculada contra la escrita y la sintaxis de diagramas.

---

## 3. Compatibilidad con Agentes Modernos y Estándares de la Industria

### 3.1 Adoptar `AGENTS.md` desde ahora
* **Qué es:** `AGENTS.md` es el estándar abierto respaldado por la Linux Foundation para dar contexto a asistentes de código en repositorios (leído nativamente por Claude Code, Cursor, Copilot Workspace, etc.).
* **Recomendación:** Agrega un archivo `AGENTS.md` minimalista (6 a 10 líneas) en la raíz que simplemente redirija a la documentación del arnés:
  ```markdown
  # Instrucciones para Asistentes y Agentes de IA
  Este repositorio opera bajo el método de "Arnés y Tareas Delimitadas".
  Antes de generar código o proponer cambios, es OBLIGATORIO leer:
  - Reglas de entrega y restricciones: docs/00-LEEME-IA.md
  - Estado del proyecto y convenciones: docs/README.md
  ```
  Esto no cuesta nada en tokens y garantiza que si el repo se abre en cualquier editor agéntico, este respete de inmediato las reglas del arnés.

### 3.2 Desacoplar definitivamente `puml-diagramas` de Django
* Para que la plantilla cumpla su promesa de ser 100% agnóstica de stack en el portafolio:
  - Mover `django2puml.py` a una carpeta de utilidades opcionales (`extras/` o `contrib/`).
  - La skill principal debe tomar como fuente directa `docs/modelo.md`, que es un formato neutro generado por `init_diseno.py`.

---

## 4. Estrategia de Portafolio y Marca Personal (CV)

Para que este proyecto destaque ante reclutadores o evaluadores técnicos:

1. **Evitar la palabra "Plantilla" en el título principal:**
   - En lugar de *"plantilla-proyecto"*, usar un nombre con mayor peso de ingeniería:
     - `ai-harness-framework`
     - `spec-driven-ai-workflow`
     - `deterministic-ai-dev-harness`
2. **Escribir un README de vitrina con un diagrama visual:**
   - Un diagrama de flujo (con Mermaid o PlantUML) que muestre el ciclo:
     $$\text{Diseño} \longrightarrow \text{Diagramas} \longrightarrow \text{Plan por Olas} \longrightarrow \text{Arnés / Tests} \longrightarrow \text{Parche Verificado}$$
   - Citar explícitamente los referentes conceptuales: *Harness Engineering (Thoughtworks / Fowler)*, *Test-Driven Development con LLMs* y *Aislamiento de contexto por tareas*.
3. **Métricas de ahorro de tokens:**
   - En el README final, incluir una comparativa real: cuántos tokens gasta un chat descontrolado versus cuántos tokens gasta una tarea empaquetada con `bundle.py` y resuelta con un parche unificado.

---

## 5. Hoja de Ruta Inmediata Sugerida (Próximos 3 Pasos)

```
[Paso 1: Confirmar Línea Base]
  └── Correr `python -m unittest discover -s tools/tests` en tu PowerShell local.
  └── Confirmar que el parche Nivel 1 está limpio en git.

[Paso 2: Desarrollar `aplicar.py`]
  └── Elimina la fricción manual de aplicar parches en Windows.
  └── Incluye la guarda de tests antes de permitir el commit.

[Paso 3: Parche de Formatos Nivel 2 + App Piloto]
  └── Aplicar los formatos del Nivel 2 (`cambio.md`, `tarjeta.md` con modos).
  └── Arrancar una app pequeña de prueba para validar el flujo antes de construir el resto de tools.
```
