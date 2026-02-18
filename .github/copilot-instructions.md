# Instrucciones para Copilot – Revisión de código Odoo (v18.0)

## Contexto

* El repositorio contiene **módulos Odoo preparados para Odoo 18** (rama `18.0`).
* El objetivo es **revisar cambios de código** y **sugerir mejoras seguras y relevantes**, sin caer en micro-comentarios.

---

## Reglas generales (aplican a todo el código)

1. **Responder siempre en español.**
2. Detectar y corregir **errores de tipeo u ortografía evidentes** en nombres de variables, métodos o comentarios (cuando sean claros).
3. No sugerir traducciones de docstrings o comentarios entre idiomas (no proponer pasar del inglés al español o viceversa).
4. No proponer agregar docstrings si el método no tiene uno.

   * Si ya existe un docstring, puede sugerirse un estilo básico acorde a PEP8, pero **no será un error** si faltan `return`, tipos o parámetros documentados.
5. No proponer cambios puramente estéticos (espacios, comillas simples vs dobles, orden de imports, etc.).
6. Mantener el feedback **muy conciso** en los PRs: priorizar pocos puntos claros, evitar párrafos largos y no repetir el contexto que ya está explicado en la descripción del PR.
7. Sobre traducciones: usar `_()` o `self.env._()` es indistinto; solo marcar si hay mensajes de error o textos no traducidos que deban serlo.

---

## Revisión de modelos (`models/*.py`) – cuestiones generales

* Verificar que:

  * Los campos (`fields.*`) tengan nombres claros, consistentes y no entren en conflicto con otros módulos.
  * Las relaciones (`Many2one`, `One2many`, `Many2many`) estén bien definidas y referencien modelos válidos, con `ondelete` apropiado.
  * Las constraints declaradas con `_sql_constraints` o `@api.constrains` mantengan la integridad esperada y mensajes claros.
* Sugerir uso de `@api.depends` si un campo compute carece de dependencias explícitas.
* Si se redefine un método de Odoo, asegurar que se llama correctamente `super()`, manteniendo el contrato original.
* Si hay lógica nueva, evitar loops costosos con búsquedas dentro de iteraciones; sugerir `mapped`, `filtered`, dominios vectorizados u otras formas más eficientes.

---

## 🧾 Revisión del manifest (`__manifest__.py`) – reglas generales

* Confirmar que todos los archivos usados (vistas, seguridad, datos, reportes, wizards) estén referenciados en el manifest.
* Verificar dependencias declaradas: que no falten módulos requeridos ni se declaren innecesarios.
* Solo hacerlo una vez por revisión, aunque haya múltiples archivos afectados.

---

## Revisión de vistas XML (`views/*.xml`) – reglas generales

* Confirmar que se usen herencias (`inherit_id`, `xpath`) en lugar de redefinir vistas completas sin necesidad.
* Validar que los campos referenciados existan en los modelos correspondientes.
* Evitar duplicar gran parte del `arch`; prioriza `xpath` específicos y claros.

### Notas específicas Odoo 18 (vistas / UI)

* Las vistas de lista usan el nuevo elemento `<list>` en lugar de `<tree>`; si se ve código nuevo en 18 que sigue usando `<tree>` para listas estándar, sugiere adaptarlo cuando sea coherente con el resto del módulo.
* Muchas condiciones en vistas pueden escribirse con atributos declarativos (`invisible`, `readonly`, `required`) más simples que combinaciones complejas de `attrs`; sugiere simplificar cuando el diff haga la vista más compleja sin necesidad.

---

## Seguridad y acceso – reglas generales

* Verificar los archivos `ir.model.access.csv` para nuevos modelos: deben tener permisos mínimos necesarios.
* No proponer abrir acceso global sin justificación.
* Si se cambian `record rules`, revisar especialmente combinaciones multi-compañía y multi-website.

### Seguridad y rendimiento del ORM

* Reforzar las advertencias sobre **SQL crudo**: si el diff muestra `self.env.cr.execute("...%s..." % var)` u otras interpolaciones inseguras, recomendar reemplazarlo por dominios ORM (`search`, `browse`) o, si es inevitable, parametrizar la query para heredar sanitización y reglas de acceso.
  * Ejemplo inseguro que debe marcarse: `self.env.cr.execute("SELECT * FROM res_partner WHERE email = '%s'" % email)`.
  * Variante segura aceptable: `self.env.cr.execute("SELECT * FROM res_partner WHERE email = %s", (email,))` o, mejor aún, `self.env['res.partner'].search([('email', '=', email)])`.
* Señalar cualquier uso de `eval` o construcción manual de domains a partir de input de usuario (`eval(domain_string)`), proponiendo dominios expresados como listas de tuplas o mediante objetos `Domain`.
  * Ejemplo inseguro: `records = self.env['res.partner'].search(eval("[('name','ilike','%s')]" % user_input))`.
  * Forma segura: `records = self.env['res.partner'].search([('name', 'ilike', user_input)])`.
* Vigilar patrones ineficientes comunes: bucles que ejecutan `search`/`write` por registro, filtrados manuales tras `search([])` o cómputos que podrían resolverse con `search_count`, `mapped`, `filtered` o `browse` masivo.
  * Ejemplo a señalar: `for partner_id in partner_ids: partner = self.env['res.partner'].search([('id', '=', partner_id)])`.
  * Proponer `partners = self.env['res.partner'].browse(partner_ids)` y operar sobre el recordset completo.
* Para lecturas planas o exportaciones, preferir `search_fetch(fields=...)` para limitar columnas y reducir memoria.
  * Caso ilustrativo: reemplazar listas armadas a mano con `result = self.env['res.partner'].search_fetch(domain=[('is_company', '=', True)], fields=['name', 'email', 'vat'])`.
* Recordar que los writes vectorizados (`recordset.write`) y las operaciones en lotes evitan locks prolongados y mejoran la trazabilidad de auditoría del ORM.
  * Ejemplo recomendado: `partners.write({'comment': 'Actualizado masivamente'})` en lugar de iterar y escribir registro por registro.
* Tener en cuenta la **navegación de campos relacionales** en Odoo: acceder a campos encadenados como `m.fiscal_position_id.l10n_ar_tax_ids` es seguro incluso cuando `fiscal_position_id` está vacío (devuelve un recordset vacío). Por eso, expresiones como `not m.fiscal_position_id.l10n_ar_tax_ids` ya cubren el caso en que no haya posición fiscal y **no hace falta** añadir un chequeo previo separado sobre `fiscal_position_id`.
* Revisar accesos directos por índice en listas o recordsets, por ejemplo `lines[0].id`: si el conjunto está vacío puede lanzar `IndexError`. Copilot debe sugerir patrones más seguros (por ejemplo `if lines: first = lines[0]`) o, cuando sea posible, reescribir la lógica para trabajar sobre el recordset completo en lugar de un único elemento.

---

## Cambios estructurales y scripts de migración – **cuestiones generales**

Cuando el diff sugiera **cambios de estructura de datos**, **siempre evaluar** si corresponde proponer un **script de migración** en `migrations/` (pre/post/end).

### Reglas generales de estructura de `migrations/`

* La carpeta dentro de `migrations/` debe corresponder con la versión declarada en el manifest (p. ej. `migrations/18.0.4.0/`).
* Los scripts deben ser idempotentes, trabajar en lotes y registrar logs claros.

### Ejemplos de cambios estructurales (actualizado con tus criterios)

En estos casos **normalmente corresponde** proponer migración (salvo notas en contra):

1. **Renombrar campos o modelos**

   * **Campos:** proponer migración **solo si el campo es almacenado** en base de datos:
     * campos normales (`Char`, `Many2one`, `Boolean`, etc.),
     * campos `compute` con `store=True`.
     * Campos `compute` **sin** `store=True` no requieren script por el renombre en sí (son virtuales).
   * **Modelos:** renombrar modelos **siempre** implica revisar migración (`ir.model`, `ir.model.data`, tablas relacionales, vistas, acciones…).

2. **Cambiar tipos de campo**

   * Se considera cambio estructural cuando **cambia la representación en la base de datos** (p.ej. `Char → Many2one`, `Selection → Many2one`, `Integer → Monetary`, `Many2one → Many2many`, etc.).
   * Cambios “compatibles” a nivel de PostgreSQL **no suelen requerir script**, por ejemplo:
     * `Char → Text` o ajustes de tamaño de `Char`;
     * cambios de precisión en `Float` sin cambio de semántica.
   * Aun así, si el cambio implica lógica nueva (p.ej. pasar de `Boolean` a `Selection` con múltiples estados) puede requerir mapeo de datos.

3. **Quitar campos para reestructurar información**

   * Por ejemplo, dividir un campo en varios (split) o fusionar varios en uno (merge).
   * Siempre revisar si hay datos que deban preservarse antes de eliminar el campo original.

4. **Agregar campos `compute` almacenados (`store=True`) con backfill**

   * Si el campo nuevo es `compute` y `store=True`, y se espera que tenga valor para **registros históricos**, conviene:
     * Proponer **script `post`** que haga el backfill **en lotes**.
     * Añadir una **advertencia explícita** cuando el modelo tiene muchos registros (p.ej. millones) para que el cálculo no se haga en una sola transacción que bloquee la tabla.

5. **Cambiar dominios o valores de campos `selection`**

   * **Añadir nuevos valores de `selection`**:  
     En general **no requiere migración** si solo se agregan opciones nuevas y no se tocan las existentes.
   * **Eliminar o renombrar keys existentes de `selection`**:
     * Puede dejar valores históricos huérfanos o inválidos → proponer script que mapee `old_value → new_value` o que normalice registros antiguos.
     * Mencionar que hay que tener en cuenta el comportamiento de campos relacionados (p.ej. un `Many2one` con `ondelete` específico) si el `selection` influye en lógica que crea o elimina registros.
   * **Cambios de dominio** en campos relacionales (`Many2one`, `Many2many`):
     * Si el nuevo dominio excluye valores usados históricamente, puede ser necesario limpiar o remapear datos para que no queden registros en estados imposibles.
     * Recordar que el `ondelete` del campo define qué ocurre al eliminar registros apuntados; hay que respetarlo al limpiar datos.

6. **Cambiar o añadir `_sql_constraints` (unique / index)**

   * Cambios en constraints `UNIQUE` o adición de nuevas constraints/índices pueden **fallar con datos existentes** (duplicados, valores nulos, etc.).
   * Al menos, Copilot debe:
     * emitir una **advertencia** sobre el riesgo de fallo en el upgrade,
     * sugerir revisar datos previos (y, cuando se vea necesario, un **pre-script** que limpie duplicados o normalice datos antes de aplicar la constraint).

7. **Cambios en `ir.model.data` / XML IDs**

   * Renombres de XML IDs (`module.name → module2.name2`) o cambios en `module` / `name` suelen requerir:
     * script para actualizar referencias dependientes (acciones, vistas, menús, records en otros módulos),
     * o uso de utilidades de upgrade.
   * Caso especial: registros con `no_update="1"`:
     * Si cambia solo texto/etiquetas menores, puede no hacer falta migración.
     * **Si cambia el contenido lógico** (ej. campo `domain`, configuración, secuencias) y el registro tiene `no_update="1"`, debes **sugerir forzar el cambio**:
       * vía script que actualice explícitamente los registros por su `xml_id`,
       * o mediante un proceso de “force update” apropiado.

8. **Cambios de reglas de acceso / propiedad**

   * Cambios profundos en `record rules` o en campos que determinan propiedad (company, website, owner…) pueden necesitar scripts para:
     * recomputar propiedad,
     * asignar company/website por defecto,
     * o migrar datos entre reglas.

> **Nota:** No se incluye en esta lista el caso “Añadir `required=True` a campos existentes sin default” como condición automática de migración; Copilot no debe sugerir script de migración **solo** por ese motivo, salvo que en el diff se vea claro que hay datos históricos incompatibles.

---

## Scripts de migración en `migrations/`: pre / post / end (reglas generales)

> **Objetivo:** preservar datos y mantener instalabilidad/actualizabilidad segura.

- **pre**: Se ejecutan antes de actualizar el módulo. Útiles para preparar datos o estructuras que eviten fallos durante el upgrade.
- **post**: Se ejecutan justo después de actualizar el módulo. Ideales para recalcular datos, limpiar residuos o ajustar referencias tras el cambio.
- **end**: Se ejecutan al final de la actualización de todos los módulos. Indicados para tareas globales que dependen de múltiples módulos o para ajustes finales.

### Mapeo de cambio → acción recomendada (actualizado)

* **Rename de campo almacenado (mismo modelo)**

  * **Pre-script**: crear columna/alias temporal o copiar datos del campo viejo al nuevo antes de que Odoo toque el esquema, si el cambio puede romper constraints.
  * **Post-script**: limpieza de residuos, recomputes de campos derivados si aplica.

* **Renombrar modelo**

  * **Pre-script**: preparar mapeos en `ir.model` y `ir.model.data`, y ajustar referencias técnicas si es necesario.
  * **Post-script**: re-enlazar vistas, acciones, menús, reglas y volver a chequear accesos.

* **Eliminar campo y mover datos a otros campos (split/merge)**

  * **Pre-script**: copiar datos a los nuevos campos (cuando sea posible) antes de que el schema elimine la columna original.
  * **Post-script**: normalizar referencias, recalcular computes, limpiar helpers.

* **Agregar campo `compute` con `store=True`**

  * **Pre-script (opcional y solo en modelos muy grandes)**: crear columna en DB o preparar estructura para evitar locks largos.
  * **Post-script (recomendado)**: backfill **en lotes** para poblar el valor almacenado; es importante para modelos con muchos registros.

* **Cambiar tipo de campo con cambio real de representación**

  * **Pre-script**: crear columna temporal con el nuevo tipo y migrar datos (con conversión).
  * **Post-script**: intercambiar/renombrar columnas, borrar la vieja, disparar recomputes si hace falta.

* **Cambios en `selection` (eliminar/renombrar keys existentes)**

  * **Pre-script**: mapear valores antiguos → nuevos (tabla de mapeo) usando helpers como `change_field_selection_values()` cuando aplique.
  * **Post-script**: validar que no quedan valores huérfanos y que las reglas de negocio siguen cumpliéndose.
  * **Añadir keys nuevas**: **no proponer script** salvo que el diff muestre una migración masiva explícita de valores.

* **Nuevas constraints `_sql_constraints` (unique) / índices**

  * **Pre-script (recomendado cuando haya riesgo)**: detectar y resolver duplicados o datos inconsistentes antes de crear la constraint.
  * **Post-script**: crear el índice/constraint y, si procede, validar que no haya fallos.

* **Cambios en registros XML con `no_update="1"`**

  * **Post-script**: actualizar esos registros por API (respetando `xml_id`) cuando el contenido lógico haya cambiado y no vaya a ser reaplicado por el upgrade normal.

* **Cambios de reglas de acceso / multi-company / multi-website**

  * **Pre- o post-script** según el caso, para rellenar campos obligatorios (company, website, owner) y evitar que registros queden inaccesibles.

> **Regla general:** si el cambio puede **romper durante el upgrade**, usa **pre-script**; si requiere **recalcular o reaplicar** después del código nuevo, usa **post-script**. Si se necesita una acción global al final, usa **end-script**.

---

## Cobertura de tests automatizados – reglas generales

* Cuando el diff introduzca **funcionalidad nueva no trivial** (nuevos métodos con lógica compleja, nuevos flujos de negocio, refactors grandes, nuevas APIs, etc.), revisar si existe cobertura de tests razonable para esos cambios.
* Si no se ve una cobertura clara, sugerir de forma **concreta y breve** qué tipo de test añadir (unitarios de modelo, tests de wizards, tours, pruebas sobre reportes, etc.), sin exigir una suite completa para cada cambio.
* Para cambios pequeños o puramente cosméticos (ajustes en textos, vistas simples, pequeñas correcciones) **no hace falta** proponer la creación de tests nuevos.

---

## Convenciones de scripts en `migrations/` (generales)

* Ubicación: `migrations/<module_version>/`.
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
# migrations/<module_version>/pre_rename_partner_ref.py
from odoo import api, SUPERUSER_ID

def migrate(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    partners = env['res.partner'].with_context(active_test=False).search([('old_ref', '!=', False)])
    for batch in range(0, len(partners), 500):
        sub = partners[batch:batch+500]
        for p in sub:
            if not p.new_ref:
                p.new_ref = p.old_ref
```

```python
# migrations/<module_version>/post_backfill_stored_amount_total.py
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

## Checklist rápida para el review (general)

| Categoría          | Qué comprobar Copilot                                                                                    |
| ------------------ | -------------------------------------------------------------------------------------------------------- |
| Modelos            | Relaciones válidas; constraints; uso adecuado de `@api.depends`; `super()` correcto                      |
| Vistas XML         | Herencias correctas; campos válidos; adaptación a cambios de versión (p.ej. `<list>` vs `<tree>`)        |
| Seguridad          | Accesos mínimos necesarios; reglas revisadas                                                             |
| Migraciones        | **Si hay cambios estructurales, sugerir script en `migrations/` (pre/post/end)** y describir qué hace    |
| Rendimiento / ORM  | Evitar loops costosos; no SQL innecesario; aprovechar las optimizaciones del ORM de la versión           |
| Ortografía & typos | Errores evidentes corregibles sin modificar idioma ni estilo                                             |

---

## Estilo del feedback (general)

* Ser breve, claro y útil. Ejemplos:

  * “El campo `partner_id` no se encuentra referenciado en la vista.”
  * “Este método redefine `write()` sin usar `super()`.”
  * “Tip: hay un error ortográfico en el nombre del parámetro.”
  * **Migración:** “Se renombra `old_ref` → `new_ref`: falta **pre-script** en `migrations/` para copiar valores antes del upgrade; añadir **post-script** para recompute del stored.”

* Evitar explicaciones largas o reescrituras completas salvo que el cambio sea claro y necesario.
* Priorizar comentarios en forma de **lista corta de puntos** (3–7 ítems) y frases breves en lugar de bloques de texto extensos.

---

## Resumen operativo para Copilot

1. **Si hay cambio estructural (según la lista actualizada) → propone y describe script(s) de migración en `migrations/` (pre/post/end)**, con enfoque idempotente y en lotes.
2. Distingue entre:

   * **cuestiones generales** (válidas para cualquier versión),
   * y **matices específicos de Odoo 18** (por ejemplo, uso de `<list>`, passkeys, tours y comportamiento del framework).

3. Mantén el feedback **concreto, breve y accionable**.