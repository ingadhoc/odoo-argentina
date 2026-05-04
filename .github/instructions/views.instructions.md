---
applyTo:
  - "**/views/**/*.xml"
  - "**/reports/**/*.xml"
  - "**/data/**/*.xml"
---

# Revisión de vistas XML y QWeb

## Herencia

- Usar `inherit_id` + `xpath` específico en vez de redefinir la vista entera.
- `xpath` debe apuntar a un elemento único y estable: preferir `//field[@name='...']` o `//group[@name='...']` antes que índices de `child::`.
- Evitar `position="replace"` cuando `position="attributes"` o `position="after"/"before"/"inside"` alcanza.
- No duplicar grandes bloques de `arch`: heredar y sobreescribir lo mínimo necesario.

## Campos referenciados

- Todo `<field name="...">` debe existir en el modelo correspondiente (y ser accesible por el usuario).
- Campos usados en atributos como `invisible="..."`, `readonly="..."`, `required="..."` también deben estar declarados en la vista (si no, agregar con `invisible="1"`).

## Atributos dinámicos (Odoo 17+)

- `attrs="{'invisible': [...]}"` **deprecado**. Usar atributos directos: `invisible="field == 'done'"`, `readonly="state in ['done','cancel']"`, `required="type_id"`.
- Expresiones en atributos usan sintaxis Python sobre los campos disponibles del registro actual.
- En listas (`<list>`): para campos que nunca se muestran, usar `column_invisible="1"` en vez de `invisible="1"` (evita cargar valores innecesariamente).

## `<list>` vs `<tree>` (Odoo 19)

- Odoo 19 usa `<list>` en vez de `<tree>` como tag de lista.
- Atributos frecuentes: `editable="bottom"`, `multi_edit="1"`, `decoration-*`, `optional="show|hide"` en fields.
- Si el diff introduce `<tree>` en módulo v19 → marcar como cambio obligatorio a `<list>`.

## Kanban y QWeb

- **Odoo 19+**: templates kanban usan `t-name="card"` (antes `t-name="kanban-box"`).
- `t-esc` deprecado → usar `t-out` para escribir valores (aplica a todas las versiones recientes).
- `t-options-widget` sólo sobre campos; no abusar.

## Búsquedas y filtros

- Filtros de búsqueda sobre campos no indexados en datasets grandes → sugerir `index=True` en el field o filtro alternativo.
- `<filter name="..." domain="...">` debe tener `name` único para poder heredarse.

## Acciones y menús (cuando vengan en el mismo diff)

- `ir.actions.act_window` debe declarar `res_model`; `view_mode` consistente con vistas existentes.
- Menús heredados con `parent_id` correcto; evitar duplicación de `sequence`.
- Nuevos menús deben tener permisos coherentes (grupo o reglas ACL).

## Datos XML

- `<record>` nuevos deben tener `id` con convención `module_<modelo>_<descripcion>`.
- Usar `noupdate="1"` con cuidado: si más adelante cambia el contenido lógico, requiere script de migración forzando el update por `xml_id`.
- No mezclar datos de demo con datos funcionales (carpetas `data/` vs `demo/` y declaración en manifest).

## Reportes QWeb

- Templates deben heredar estilos base (`web.external_layout` o similar) en vez de duplicar CSS inline.
- `t-call` para layouts; `t-field` para renderizar valores con su widget; `t-out`/`t-esc` ya no es necesario si se usa `t-field`.
