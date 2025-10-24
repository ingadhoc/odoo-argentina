
# Instrucciones para Copilot – Revisión de código Odoo (v19.0)

## Contexto

* El repositorio contiene **módulos Odoo** compatibles con la versión **v19.0** (o versiones compatibles cercanas).
* El objetivo es **revisar cambios de código** y **sugerir mejoras seguras y relevantes**, sin hacer revisiones excesivamente estrictas.

---

## Reglas generales

1. **Responder siempre en español.**
2. Detectar y corregir **errores de tipeo u ortografía evidentes** en nombres de variables, métodos o comentarios (cuando sean claros).
3. No sugerir traducciones de docstrings o comentarios entre idiomas (no proponer pasar del inglés al español o viceversa).
4. No proponer agregar docstrings si el método no tiene uno.

   * Si ya existe un docstring, puede sugerirse un estilo básico acorde a PEP8, pero **no será un error** si faltan `return`, tipos o parámetros documentados.
5. No proponer cambios puramente estéticos (espacios, comillas simples vs dobles, orden de imports, etc.).

---

## Revisión de modelos (`models/*.py`)

* Verificar que:

  * Los campos (`fields.*`) tengan nombres claros, consistentes y no entren en conflicto con otros módulos.
  * Las relaciones (`Many2one`, `One2many`, `Many2many`) estén bien definidas y referencien modelos válidos.
  * Las constraints declaradas con `_sql_constraints` o `@api.constrains` mantengan la integridad esperada.
  * NOTA: En v19 se definen con `models.Constraint`
  * Los índices tradicionalmente se definían en `_sql_constraints = [('unique_name', 'UNIQUE(name)', 'mensaje')]`.
  * NOTA: En v19 usar `models.Index("campo")` para índices normales y `models.UniqueIndex("campo", "mensaje")` para únicos.
* Sugerir uso de `@api.depends` si un campo compute carece de dependencias explícitas.
* Si se redefine un método de Odoo, asegurar que se llama correctamente `super()`, manteniendo el contrato original.
* Si hay lógica nueva, evitar loops costosos con búsquedas dentro de iteraciones; sugerir `mapped`, `filtered` u otras formas más eficientes.

---

## 🧾 Revisión del manifest (`__manifest__.py`)

* Confirmar que todos los archivos usados (vistas, seguridad, datos, reportes, wizards) estén referenciados en el manifest.
* Verificar dependencias declaradas: que no falten módulos requeridos ni se declaren innecesarios.
* **Regla de versión (obligatoria):**
  Siempre que el diff incluya **modificaciones en**:

  * definición de campos o modelos (`models/*.py`, `wizards/*.py`),
  * vistas o datos XML (`views/*.xml`, `data/*.xml`, `report/*.xml`, `wizards/*.xml`),
  * seguridad (`security/*.csv`, `security/*.xml`),
    **y el `__manifest__.py` no incrementa `version`, sugerir el bump de versión** (por ejemplo, `1.0.0 → 1.0.1`).
  * Solo hacerlo una vez por revisión, aunque haya múltiples archivos afectados.

---

## Revisión de vistas XML (`views/*.xml`)

* Confirmar que uses herencias (`inherit_id`, `xpath`) efectivamente, no redefiniciones completas innecesarias.
* Validar que los campos referenciados en la vista existan en los modelos correspondientes.
* Atento a cambios en versiones nuevas de Odoo:

  * En Odoo 18, el elemento `<tree>` fue reemplazado por `<list>` en vistas de tipo lista.
  * Odoo 18 simplificó atributos condicionales: `attrs`/`states` pueden reemplazarse por condiciones directas (`invisible="..."`, `readonly="..."`) cuando aplique.
* Sugerir no duplicar vistas ni redefinir todo el `arch` si puede hacerse con `xpath`.

---

## Seguridad y acceso

* Verificar los archivos `ir.model.access.csv` para nuevos modelos: deben tener permisos mínimos necesarios.
* No proponer abrir acceso global sin justificación.
* Si se agregan nuevos modelos o campos de control de acceso, **recordar el bump de versión** (ver sección de manifest).

---

## Detección de cambios estructurales (esquema / datos)

Cuando el diff sugiera **cambios de estructura de datos**, **siempre proponer** un **script de migración** en la carpeta `migrations/`, usando pre/post/end según corresponda (ver mapeo más abajo) **y recordar el bump de versión**.
Ejemplos de cambios estructurales:

* Carpeta dentro de `migrations/` debe ser la versión correspondiente en el manifest (e.g. `migrations/18.0.5.0/`).
* Renombrar campos o modelos.
* Cambiar tipos de campo (e.g. `Char → Many2one`, `Selection → Many2one`, etc.).
* Quitar campos para reestructurar información en otros (split/merge).
* Agregar campos `compute` **almacenados** (`store=True`) que requieren backfill.
* Cambiar dominios/valores de `selection` (añadir/eliminar/renombrar keys).
* Añadir `required=True` a campos existentes sin default en datos históricos.
* Cambiar o añadir `_sql_constraints` (unique/index) que puedan fallar con datos existentes.
* Cambios en `ir.model.data`/XML IDs (renombres, `no_update="1"`, cambios de `module`/`name`).
* Cambios de reglas de acceso que requieran recalcular propiedad/propagación.

---

## Scripts de migración en `scripts/`: pre / post / end

> **Objetivo:** preservar datos y mantener instalabilidad/actualizabilidad segura.

- **pre**: Se ejecutan antes de actualizar el módulo. Útiles para preparar datos o estructuras que eviten fallos durante el upgrade.
- **post**: Se ejecutan justo después de actualizar el módulo. Ideales para recalcular datos, limpiar residuos o ajustar referencias tras el cambio.
- **end**: Se ejecutan al final de la actualización de todos los módulos. Indicados para tareas globales que dependen de múltiples módulos o para ajustes finales.

### Mapeo de cambio → acción recomendada

* **Rename de campo (mismo modelo)**

  * **Pre-script**: copiar datos del campo viejo al nuevo (o crear alias temporal) para no perder datos tras el upgrade.
  * **Post-script**: limpieza de residuos, recomputes si aplica.

* **Eliminar campo y mover datos a otros campos (split/merge)**

  * **Pre-script**: crear campos destino (si es viable vía SQL/DDL) y migrar datos intermedios.
  * **Post-script**: normalizar referencias, recalcular computes, borrar helpers.

* **Cambios en registros XML con `no_update="1"`**

  * **Post-script**: usar **force upgrade** (reaplicar datos) o actualizar esos registros por API (respetando `xml_id`) para reflejar cambios.

* **Agregar campo `compute` con `store=True`**

  * **Pre-script (opcional si alto volumen/incidencia)**: crear columna en DB para evitar lock prolongado en upgrade.
  * **Post-script**: backfill **en lotes** (batch) para poblar el valor almacenado.

* **Cambiar tipo de campo**

  * **Pre-script**: crear columna temporal con tipo nuevo y migrar datos (con conversión).
  * **Post-script**: swap/renombrar columnas, borrar columna vieja, recomputes.

* **Cambios en `selection` (renombre/elim./nuevo valor default)**

  * **Pre-script**: mapear valores antiguos → nuevos (tabla de mapeo).
  * **Post-script**: validar que no quedan valores huérfanos.

* **Agregar `required=True` a campo existente**

  * **Pre-script**: asignar default consistente a registros históricos (en lote) o rellenar desde lógica derivada.
  * **Post-script**: constraint check.

* **Nuevas `_sql_constraints` (unique) / índices**

  * **Pre-script**: detectar y resolver duplicados o inconsistencias.
  * **Post-script**: crear índice/constraint y verificar.

* **Renombrar modelo**

  * **Pre-script**: crear `ir.model.data`/mapeos, migrar `model` en `ir.model.data` y tablas rel.
  * **Post-script**: re-enlazar vistas, acciones, reglas y volver a chequear accesos.

* **Cambios en XML IDs o modularización**

  * **Pre-script**: preparar mapeo `old_xmlid → new_xmlid`.
  * **Post-script**: actualizar referencias dependientes; si está marcado `no_update`, aplicar actualización manual.

> **Regla general:** si el cambio puede **romper durante el upgrade**, prepara **pre-script**; si requiere **recalcular o reaplicar** después del código nuevo, usa **post-script**. Si se necesita una acción global al final, usa **end-script**.

---

## Convenciones de scripts en `migrations/`

* Ubicación: `migrations/`
* Nombres sugeridos:

  * `pre_<breve-descripcion>.py`
  * `post_<breve-descripcion>.py`
* Requisitos:

  * Idempotentes (seguros si se ejecutan más de una vez).
  * En lotes (`batch_size` razonable) para datasets grandes.
  * Logs claros (uso de `_logger.info`).
  * Manejo de transacciones cuando aplique (evitar locks largos).
  * Documentar al inicio **qué suponen** y **qué garantizan**.

**Esqueleto mínimo (ejemplo):**

```python
# migrations/18.0.4.0/pre_rename_partner_ref.py
from odoo import api, SUPERUSER_ID

def migrate(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Ejemplo: copiar datos de 'old_ref' a 'new_ref' antes del upgrade
    partners = env['res.partner'].with_context(active_test=False).search([('old_ref', '!=', False)])
    for batch in range(0, len(partners), 500):
        sub = partners[batch:batch+500]
        for p in sub:
            if not p.new_ref:
                p.new_ref = p.old_ref
```

```python
# migrations/18.0.4.0/post_backfill_stored_amount_total.py
from odoo import api, SUPERUSER_ID

def migrate(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Orders = env['sale.order'].with_context(active_test=False)
    ids = Orders.search([]).ids
    for i in range(0, len(ids), 200):
        batch = Orders.browse(ids[i:i+200])
        # Forzar recompute del stored
        batch._compute_amount_total()
```

---

## Checklist rápida para el review

| Categoría          | Qué comprobar Copilot                                                                                    |
| ------------------ | -------------------------------------------------------------------------------------------------------- |
| Modelos            | Relaciones válidas; constraints; uso adecuado de `@api.depends`; `super()` correcto                      |
| Vistas XML         | Herencias correctas; campos válidos; adaptación a cambios de versión (p.ej. `<list>` vs `<tree>`)        |
| Manifest           | **Bump de versión obligatorio** si hay cambios en modelos/vistas/seguridad/datos; archivos referenciados |
| Seguridad          | Accesos mínimos necesarios; reglas revisadas                                                             |
| Migraciones        | **Si hay cambios estructurales, exigir script en `migrations/` (pre/post/end)** y describir qué hace     |
| Rendimiento / ORM  | Evitar loops costosos; no SQL innecesario; aprovechar mejoras de v19.0                            |
| Ortografía & typos | Errores evidentes corregibles sin modificar idioma ni estilo                                             |

---

## Heurística práctica para el bump de versión

* **SI** el diff toca cualquiera de: `models/`, `views/`, `data/`, `report/`, `security/`, `wizards/`
  **Y** `__manifest__.py` no cambia `version` → **Sugerir bump**.
* **SI** hay scripts `migrations/pre_*.py` o `migrations/post_*.py` nuevos → **Sugerir al menos minor bump**.
* **SI** hay cambios que rompen compatibilidad (renombres, tipos, required sin default) → **Sugerir minor/major** según impacto.

---

## Casos adicionales a cubrir (sugiere migración si aplica)

* Introducción de **nuevos defaults** que dependen de datos existentes.
* Cambio en **nombres técnicos** de vistas/acciones/menús (asegurar que `xml_id` no cambie o mapearlo).
* **Indexaciones** nuevas (agregar índices en post para minimizar locks; validar cardinalidad).
* Normalización de **monedas/impuestos** (migrar valores legacy; recalcular montos).
* Cambios en **multi-company** o **multi-website** (poblar valores por compañía/sitio).
* Ajustes en **traducciones** críticas de `selection` (asegurar mapping por key, no por etiqueta traducida).

---

## Estilo del feedback

* Ser breve, claro y útil. Ejemplos:

  * “El campo `partner_id` no se encuentra referenciado en la vista.”
  * “Este método redefine `write()` sin usar `super()`.”
  * “Tip: hay un error ortográfico en el nombre del parámetro.”
  * **Bump + migración:** “Se renombra `old_ref` → `new_ref`: falta **bump de versión** y **pre-script** en `migrations/` para copiar valores antes del upgrade; añadir **post-script** para recompute del stored.”

* Evitar explicaciones largas o reescrituras completas salvo que el cambio sea claro y necesario.

---

## Resumen operativo para Copilot

1. **Detecta cambios en modelos/vistas/seguridad/datos → exige bump de `version` en `__manifest__.py`.**
2. **Si hay cambio estructural → propone y describe script(s) de migración en `migrations/` (pre/post/end),** con enfoque idempotente y en lotes.
3. Mantén el feedback **concreto, breve y accionable**.
