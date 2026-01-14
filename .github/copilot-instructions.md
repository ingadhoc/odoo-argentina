# Instrucciones para Copilot – Revisión de código Odoo (v19.0)

## Contexto

* El repositorio contiene **módulos Odoo preparados para Odoo 19** (rama `19.0`).
* A nivel técnico, Odoo 19 trae **mejoras importantes en el ORM**:

  * nueva API de constraints e índices (`models.Constraint`, `models.Index`, `models.UniqueIndex`),
  * nueva forma de definir dominios via clase `Domain`,

    * Permite utilizar operadores &, | y ~ para combinar condiciones de forma más legible y mantenible.
    * Se pueden utilizar sobre función `filtered`.
    * También se puede usar `Domain('field', 'op', 'value')` o `Domain(domain)` donde domain es una lista como era habitual `[('field_1', 'op1', 'value1'), ('field_2', 'op2', 'value2'), ...]`.
  * nueva API para manejo de progresos en crons,

    * Se cambia `notify_progress` por `commit_progress` en crons, ej.

      ```python
      self.env["ir.cron"]._commit_progress(remaining=n)
      ...
      self.env["ir.cron"]._commit_progress(processed=m)
      ```

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

  * Los campos (`fields.*`) tengan nombres claros, consistentes y sin conflictos.
  * Las relaciones (`Many2one`, `One2many`, `Many2many`) tengan `comodel_name` y `ondelete` adecuados.
  * Las constraints (`_sql_constraints`, `@api.constrains`) mantengan integridad y mensajes claros.
* Sugerir `@api.depends` cuando un campo `compute` no lo tenga y dependa de otros campos.
* En métodos redefinidos, verificar uso de `super()` y respeto del contrato original.
* Evitar patrones ineficientes (búsquedas dentro de loops, write uno a uno, etc.) y favorecer operaciones vectorizadas.

### Notas específicas Odoo 19 (modelos / ORM)

* En Odoo 19 se recomienda usar las nuevas clases `models.Constraint`, `models.Index` y `models.UniqueIndex` para definir constraints e índices a nivel de modelo, en lugar de depender exclusivamente de `_sql_constraints`.([Odoo][4])

  * Copilot puede sugerir migrar definiciones nuevas de `_sql_constraints` a la nueva API cuando el diff ya está tocando esas partes.
* El tiempo de inicialización del registro de modelos se ha reducido de manera notable, lo que vuelve todavía más relevante evitar invalidaciones innecesarias y recomputes costosos en métodos `create`/`write`/`unlink`.([glo][2])

---

## 🧾 Revisión del manifest (`__manifest__.py`) – reglas generales

* Confirmar que todos los archivos usados (vistas, seguridad, datos, reportes, wizards) estén referenciados en el manifest.
* Verificar dependencias declaradas: que no falten módulos requeridos ni se declaren innecesarios.
* **Regla de versión (obligatoria):**
  Solo sugerir bump de versión si el `__manifest__.py` no incrementa `version` y se modificó la estructura de un modelo, una vista, o algún record .xml (ej. cambios en definición de campos, vistas XML, datos XML, seguridad).
* Solo hacerlo una vez por revisión, aunque haya múltiples archivos afectados.

---

## Revisión de vistas XML (`views/*.xml`) – reglas generales

* Confirmar que se usen herencias (`inherit_id`, `xpath`) en lugar de redefinir vistas completas sin necesidad.
* Validar que los campos referenciados existan en los modelos correspondientes.
* Evitar duplicar gran parte del `arch`; prioriza `xpath` específicos y claros.

---

## Seguridad y acceso – reglas generales

* Verificar los archivos `ir.model.access.csv` para nuevos modelos: deben tener permisos mínimos necesarios.
* No proponer abrir acceso global sin justificación.
* Si se agregan nuevos modelos o campos de control de acceso, **recordar el bump de versión** (ver sección de manifest).
* En Odoo 19, poner atención especial a cambios de seguridad ligados a:

  * integraciones de IA,
  * VOIP, WhatsApp y mensajería,
  * nuevos objetos de Equity/ESG.

  Cambios en estos modelos pueden requerir migración de ownership/tokens o datos de permisos.([Odoo][1])

### Seguridad y rendimiento del ORM

* Detectar cualquier `self.env.cr.execute` con interpolación directa de parámetros y reemplazarlo por dominios ORM o queries parametrizadas (`execute(sql, params)`).
  * Marcar ejemplos como `self.env.cr.execute("SELECT id FROM res_partner WHERE name = '%s'" % name)` y sugerir el dominio equivalente `self.env['res.partner'].search([('name', '=', name)])`.
* Si se ve `eval()` o domains construidos como strings a partir de input externo, advertir del riesgo de ejecución arbitraria y sugerir el uso de objetos `Domain` o listas de tuplas.
  * Ejemplo a evitar: `domain = "[('name','ilike','%s')]" % user_input; records = self.env['res.partner'].search(eval(domain))`.
  * Alternativa segura: `records = self.env['res.partner'].search([('name', 'ilike', user_input)])` o `Domain([('name', 'ilike', user_input)])`.
  * Nota: En Odoo 19, `Domain('field', 'op', 'value')` es válido y no debe marcarse como incorrecto. Los operadores `&`, `|` y `~` pueden usarse sobre instancias de `Domain` para combinar condiciones.
* Reforzar las recomendaciones de rendimiento conocidas: evitar `search([])` seguido de filtrado en Python, evitar loops con `write`/`search` uno a uno, y proponer alternativas como `search_count`, `mapped`, `filtered`, `browse(ids)` o `search_fetch` para lecturas planas.
  * Ejemplo de mejora: usar `gmail_count = self.env['res.partner'].search_count([('email', 'ilike', 'gmail')])` en lugar de recorrer todos los partners buscando “gmail”.
  * Para lecturas masivas, preferir `names = partners.mapped('name')` frente a acumular manualmente en un bucle, y usar `search_fetch` cuando se necesiten diccionarios planos.
* En operaciones masivas, promover writes vectorizados y recomputes en lotes; en v19 se pueden combinar con `env.cr.commit()` controlado o helpers de progreso (`_commit_progress`) cuando el diff ya manipula crons.
  * Ejemplo sugerido: `partners.write({'comment': 'Actualizado masivamente'})` y `_commit_progress(processed=len(partners))` en jobs largos.
* Recordar que estas prácticas no solo mejoran performance: al mantenerse dentro del ORM se heredan los controles de acceso, auditoría y reglas multi-compañía.
* Tener en cuenta la **navegación de campos relacionales** en Odoo: acceder a campos encadenados como `m.fiscal_position_id.l10n_ar_tax_ids` es seguro incluso cuando `fiscal_position_id` está vacío (devuelve un recordset vacío). Por eso, expresiones como `not m.fiscal_position_id.l10n_ar_tax_ids` ya cubren el caso en que no haya posición fiscal y **no hace falta** añadir un chequeo previo separado sobre `fiscal_position_id`.
* Revisar accesos directos por índice en listas o recordsets, por ejemplo `lines[0].id`: si el conjunto está vacío puede lanzar `IndexError`. Copilot debe sugerir patrones más seguros (por ejemplo `if lines: first = lines[0]`) o, cuando sea posible, reescribir la lógica para trabajar sobre el recordset completo en lugar de un único elemento.

---

## Cambios estructurales y scripts de migración – **cuestiones generales**

Cuando el diff sugiera **cambios de estructura de datos**, **siempre evaluar** si corresponde proponer un **script de migración** en `migrations/` (pre/post/end) **y recordar el bump de versión**.

### Reglas generales de estructura de `migrations/`

* La carpeta dentro de `migrations/` debe corresponder con la versión declarada en el manifest (p. ej. `migrations/19.0.1.0/`).
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

## Cobertura de tests automatizados – reglas generales

* Cuando el diff introduzca **funcionalidad nueva no trivial** (nuevos métodos con lógica compleja, nuevos flujos de negocio, refactors grandes, nuevas APIs, etc.), revisar si existe cobertura de tests razonable para esos cambios.
* Si no se ve una cobertura clara, sugerir de forma **concreta y breve** qué tipo de test añadir (unitarios de modelo, tests de wizards, tours, pruebas sobre reportes, etc.), sin exigir una suite completa para cada cambio.
* Para cambios pequeños o puramente cosméticos (ajustes en textos, vistas simples, pequeñas correcciones) **no hace falta** proponer la creación de tests nuevos.

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

---

## Checklist rápida para el review

| Categoría          | Qué comprobar Copilot                                                                                        |
| ------------------ | ------------------------------------------------------------------------------------------------------------ |
| Modelos            | Relaciones válidas; constraints; uso de `@api.depends`; `super()` correcto                                   |
| Vistas XML         | Herencias correctas; campos válidos; adaptación a componentes modernos (IA, secciones, etc.)                 |
| Manifest           | **Bump de versión obligatorio** si hay cambios estructurales en modelos/vistas/records .xml; archivos referenciados     |
| Seguridad          | Accesos mínimos necesarios; reglas revisadas, en especial para IA/VOIP/WhatsApp                              |
| Migraciones        | **Si hay cambios estructurales (lista actualizada), sugerir scripts en `migrations/` y describir qué hacen** |
| Rendimiento / ORM  | Evitar patrones anti-ORM; aprovechar las mejoras del ORM/registro en v19                                     |
| Ortografía & typos | Errores evidentes corregibles sin cambiar estilo                                                             |

---

## Heurística práctica para el bump de versión

* **SI** el diff modifica la estructura de un modelo, una vista, o algún record .xml (ej. cambios en definición de campos, vistas XML, datos XML, seguridad)
  **Y** `__manifest__.py` no cambia `version` → **Sugerir bump**.
* **SI** hay scripts `migrations/pre_*.py` o `migrations/post_*.py` nuevos → **Sugerir al menos minor bump**.
* **SI** hay cambios que rompen compatibilidad (renombres, tipos, limpieza agresiva de datos) → **Sugerir minor/major** según impacto.

---

## Estilo del feedback

* El feedback debe ser **breve, concreto y accionable**.
* Priorizar comentarios en forma de **lista corta de puntos** (3–7 ítems) y frases breves en lugar de bloques de texto extensos.
* Ejemplos rápidos:

  * “La constraint nueva podría definirse como `models.Constraint` en lugar de `_sql_constraints`.”
  * “La vista de cotización no está aprovechando las secciones configurables introducidas en 19.”
  * “Se renombra el campo `state` almacenado; falta bump de versión y script de migración para copiar valores antes del upgrade.”

---

## Resumen operativo para Copilot

1. **Detecta cambios estructurales en modelos, vistas o records .xml → exige bump de `version` en `__manifest__.py` si no está incrementada.**
2. **Si hay cambio estructural (según la lista actualizada) → propone y describe script(s) de migración en `migrations/` (pre/post/end)**, con enfoque idempotente y en lotes.
3. Distingue entre:

   * **cuestiones generales**,
   * y **matices específicos de Odoo 19**, por ej. preferir la nueva API de constraints/índices cuando corresponda.
4. Mantén el feedback **concreto, breve y accionable**.