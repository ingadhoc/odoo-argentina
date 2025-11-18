# Instrucciones para Copilot – Revisión de código Odoo (v19.0)

## Contexto

* El repositorio contiene **módulos Odoo preparados para Odoo 19** (rama `19.0`).
* A nivel técnico, Odoo 19 trae **mejoras importantes en el ORM**:

  * nueva API de constraints e índices (`models.Constraint`, `models.Index`, `models.UniqueIndex`),
  * nueva forma de definir dominios via clase `Domain`,

    * Permite utilizar operadores &, | y ~ para combinar condiciones de forma más legible y mantenible.
    * Se pueden utilizar sobre función `filtered`.
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
  Siempre que el diff incluya **modificaciones en**:

  * definición de campos o modelos (`models/*.py`, `wizards/*.py`),
  * vistas o datos XML (`views/*.xml`, `data/*.xml`, `report/*.xml`, `wizards/*.xml`),
  * seguridad (`security/*.csv`, `security/*.xml`),

  **y el `__manifest__.py` no incrementa `version`, sugerir el bump de versión** (por ejemplo, `1.0.0 → 1.0.1`).
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
* Reforzar las recomendaciones de rendimiento conocidas: evitar `search([])` seguido de filtrado en Python, evitar loops con `write`/`search` uno a uno, y proponer alternativas como `search_count`, `mapped`, `filtered`, `browse(ids)` o `search_fetch` para lecturas planas.
  * Ejemplo de mejora: usar `gmail_count = self.env['res.partner'].search_count([('email', 'ilike', 'gmail')])` en lugar de recorrer todos los partners buscando “gmail”.
  * Para lecturas masivas, preferir `names = partners.mapped('name')` frente a acumular manualmente en un bucle, y usar `search_fetch` cuando se necesiten diccionarios planos.
* En operaciones masivas, promover writes vectorizados y recomputes en lotes; en v19 se pueden combinar con `env.cr.commit()` controlado o helpers de progreso (`_commit_progress`) cuando el diff ya manipula crons.
  * Ejemplo sugerido: `partners.write({'comment': 'Actualizado masivamente'})` y `_commit_progress(processed=len(partners))` en jobs largos.
* Recordar que estas prácticas no solo mejoran performance: al mantenerse dentro del ORM se heredan los controles de acceso, auditoría y reglas multi-compañía.

---

## Cambios estructurales y scripts de migración – **cuestiones generales (v18+v19)**

Las mismas reglas generales descritas en la sección de Odoo 18 se aplican también aquí. Copilot debe reutilizar la misma lógica para decidir si pide migración o no:

1. Renombres de campos **almacenados** y de modelos.
2. Cambios de tipo con impacto real en la representación en DB (no para `Char → Text` u otros cambios triviales).
3. Eliminación de campos con reestructuración de datos.
4. Nuevos campos `compute` con `store=True` que requieren backfill, con advertencias en modelos muy grandes.
5. Cambios de dominios o **eliminación/renombre** de valores de `selection` (añadir keys nuevas no requiere script en general).
6. Cambios o adición de `_sql_constraints` / índices con riesgo de conflicto con datos existentes (al menos emitir **advertencia**).
7. Cambios en `ir.model.data` / XML IDs, especialmente con `no_update="1"` cuando el contenido lógico cambia (sugerir forzar el cambio).
8. Cambios de reglas de acceso / propiedad que requieran recalcular ownership o multi-company.

En caso de duda, Copilot debe:

* describir el riesgo,
* sugerir un posible enfoque de migración,
* pero **no exagerar**: si el cambio es claramente no rompedor (ej. añadir un valor extra de `selection` sin tocar los anteriores), no pedir migración.

---

## Scripts de migración en `migrations/`: pre / post / end (v19)

* Mismas definiciones y mapeo que en la sección de Odoo 18.
* En Odoo 19 se pueden mencionar utilidades de `odoo.upgrade.util` (p.ej. `change_field_selection_values`, helpers para índices y constraints) cuando el diff ya usa el módulo de upgrade.([Odoo][5])

---

## Convenciones de scripts en `migrations/` (v19)

Iguales que en 18:

* Scripts idempotentes, por lotes, con logs claros.
* Carpeta `migrations/<module_version>/` alineada con la versión del manifest.
* `pre_*.py`, `post_*.py` y/o scripts `end` según corresponda.

---

## Checklist rápida para el review (v19)

| Categoría          | Qué comprobar Copilot                                                                                        |
| ------------------ | ------------------------------------------------------------------------------------------------------------ |
| Modelos            | Relaciones válidas; constraints; uso de `@api.depends`; `super()` correcto                                   |
| Vistas XML         | Herencias correctas; campos válidos; adaptación a componentes modernos (IA, secciones, etc.)                 |
| Manifest           | **Bump de versión obligatorio** si hay cambios en modelos/vistas/seguridad/datos; archivos referenciados     |
| Seguridad          | Accesos mínimos necesarios; reglas revisadas, en especial para IA/VOIP/WhatsApp                              |
| Migraciones        | **Si hay cambios estructurales (lista actualizada), sugerir scripts en `migrations/` y describir qué hacen** |
| Rendimiento / ORM  | Evitar patrones anti-ORM; aprovechar las mejoras del ORM/registro en v19                                     |
| Ortografía & typos | Errores evidentes corregibles sin cambiar estilo                                                             |

---

## Heurística práctica para el bump de versión (v19)

* **SI** el diff toca cualquiera de: `models/`, `views/`, `data/`, `report/`, `security/`, `wizards/`
  **Y** `__manifest__.py` no cambia `version` → **Sugerir bump**.
* **SI** hay scripts `migrations/pre_*.py` o `migrations/post_*.py` nuevos → **Sugerir al menos minor bump**.
* **SI** hay cambios que rompen compatibilidad (renombres, tipos, limpieza agresiva de datos) → **Sugerir minor/major** según impacto.

---

## Estilo del feedback (v19)

* El feedback debe ser **breve, concreto y accionable**.
* Ejemplos rápidos:

  * “La constraint nueva podría definirse como `models.Constraint` en lugar de `_sql_constraints`.”
  * “La vista de cotización no está aprovechando las secciones configurables introducidas en 19.”
  * “Se renombra el campo `state` almacenado; falta bump de versión y script de migración para copiar valores antes del upgrade.”

---

## Resumen operativo para Copilot (v19)

1. **Aplicar las mismas reglas generales** que en v18 para revisión de código, manifest y migraciones.
2. **Diferenciar claramente**:

   * cambios estructurales que requieren migración (según la lista ajustada),
   * de ajustes menores que no la necesitan (p.ej. `Char → Text`, añadir valores de `selection`).
3. Tener en cuenta las **novedades de Odoo 19**:

   * preferir la nueva API de constraints/índices cuando corresponda,
   * revisar cuidadosamente vistas y permisos ligados a IA, Equity, ESG, WhatsApp, VOIP, etc.
4. Mantener un feedback **conciso y orientado a acción**, evitando micro-comentarios.

[^odoo19]: Resumen basado en las Odoo 19 Release Notes oficiales y artículos técnicos sobre cambios del ORM e índice/constraints en Odoo 19.