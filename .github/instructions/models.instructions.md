---
applyTo:
  - "**/models/**/*.py"
  - "**/wizards/**/*.py"
  - "**/wizard/**/*.py"
  - "**/report/**/*.py"
---

# Revisión de modelos Python

## Relaciones y campos

- `Many2one`/`One2many`/`Many2many` deben declarar `comodel_name` y `ondelete` apropiado. Evitar `ondelete='cascade'` sin justificación.
- Nombres de campos claros, consistentes, sin conflictos con campos heredados.
- `required=True` sin `default` **solo** si no hay datos históricos que puedan romperse. Si los hay, proponer `default` o migración.
- Campos `compute` con `store=True` que dependen de datos históricos pueden necesitar backfill (ver `migrations.instructions.md`).

## Decoradores `@api.*`

- `@api.depends` debe listar **todas** las dependencias reales, incluidas las dotted (`@api.depends('partner_id.email')`).
- `@api.constrains` **no** acepta dotted paths, solo nombres simples.
- `@api.onchange` no debe escribir a BD ni modificar campos computados.
- Evitar decoradores obsoletos: `@api.one`, `@api.multi` (Odoo 13+ no los acepta).
- **Odoo 18+**: para prevenir borrado usar `@api.ondelete(at_uninstall=False)` en vez de sobreescribir `unlink`.
- `@api.model` solo cuando el método no depende de `self` como recordset.
- `@api.model_create_multi` para métodos `create` que aceptan lista de dicts (obligatorio en Odoo 17+).

## Herencia y `super()`

- Métodos redefinidos deben llamar `super()` salvo que el contrato diga lo contrario. Preservar el tipo/shape del retorno.
- `_name` + `_inherit` juntos solo cuando se busca crear modelo nuevo (multi-table inheritance); marcar si no hay razón clara.
- No sobrescribir `create`/`write`/`unlink` solo para side effects triviales; preferir `@api.depends`, `@api.constrains` o `@api.ondelete`.

## Constraints e índices

- **Odoo 19+**: usar `models.Constraint(...)`, `models.Index(...)`, `models.UniqueIndex(...)` como declarativas a nivel de clase, en vez de `_sql_constraints`. Si el diff ya toca constraints, sugerir migrar a la nueva API.
- Mensajes de constraint deben ser traducibles (`_("...")`).
- Añadir `UNIQUE` sobre tabla con datos existentes puede fallar; ver `migrations.instructions.md`.

## ORM seguro y eficiente

- Evitar `search` dentro de loops → usar dominio con `in` sobre ids o `_read_group`.
- Evitar `write`/`create`/`unlink` uno a uno en loops → vectorizar sobre recordset.
- `create` en Odoo 17+: preferir lista de dicts `create([{...}, {...}])`.
- `mapped`, `filtered`, `search_count`, `search_fetch` antes que recorrer en Python.
- Navegación relacional segura: `rec.partner_id.email` devuelve falso si `partner_id` vacío; no duplicar el check.
- Acceso por índice (`recordset[0]`) puede lanzar `IndexError`; guardar con `if rec: ...` o rediseñar para operar sobre el recordset completo.
- Evitar `sudo()` amplio/innecesario en métodos de negocio; justificar cada uso.
- En Odoo 19, `cr.execute` crudo desaconsejado → usar clase `SQL` con `execute_query_dict()`. Si hay `cr.execute` con interpolación (`%`, f-string, `.format`) → bloqueante, ver `security.instructions.md`.

## Nombres y estilo

- Métodos privados prefijo `_`; en Odoo 19, preferir `@api.private` donde aplica.
- Métodos muy largos (>50 líneas) → sugerir split.
- Comparaciones booleanas: `if x:` / `if not x:` (no `== True` / `== False`).
- `else` después de `return` innecesario.
- Imports no utilizados deben removerse.

## Dominios

- En Odoo 19 es válido `Domain('field', 'op', 'value')` y combinar con `&`, `|`, `~`. No marcar como error.
- `Domain` permite uso en `filtered`: no hace falta convertir a lista.
- Nunca construir dominios como strings y pasarlos por `eval` (ver `security.instructions.md`).

## Selecciones

- Agregar nuevos values a un `selection` **no** requiere migración.
- Renombrar/eliminar keys existentes → proponer script que mapee `old → new` (ver `migrations.instructions.md`).
