---
applyTo:
  - "**/__manifest__.py"
---

# Revisión de `__manifest__.py`

## Archivos referenciados

- Todo archivo usado por el módulo (vistas, seguridad, datos, reportes, wizards, demo) debe estar listado en alguna de las claves del manifest (`data`, `demo`, `assets`).
- Si un archivo XML/CSV se borra del módulo, debe removerse del manifest; si se agrega uno nuevo, debe incluirse.
- Orden relativo importa: datos de seguridad antes de datos que los referencian; vistas después de sus modelos.

## Dependencias (`depends`)

- Deben listarse todos los módulos cuyos modelos/vistas/xml_ids se usan directamente.
- **No** declarar dependencias innecesarias (infla el árbol de instalación).
- Módulos de localización (`l10n_*`) solo cuando el módulo depende funcionalmente; no por conveniencia.

## Versión

- Formato `<serie>.<mayor>.<menor>.<patch>` (ej. `19.0.1.0.0`). La serie (`19.0`, `18.0`) debe coincidir con la rama y la versión de Odoo target.
- **Regla obligatoria de versión**: cualquier cambio estructural que requiera script en `migrations/` debe **bumpear la versión** del módulo, y la carpeta bajo `migrations/` debe coincidir.
- Solo comentar la versión **una vez por revisión**, aunque haya múltiples archivos afectados.

## Metadatos

- `name`, `summary`, `description` deben estar definidos y ser consistentes.
- `author`, `license` presentes. En Adhoc, típicamente `"ADHOC SA"` y licencia según convención del repo.
- `category` coherente con el tipo de módulo.
- `installable: True` salvo que explícitamente esté siendo discontinuado.
- `application: True` solo para módulos que deben aparecer como aplicación raíz (no para sub-módulos).

## Assets (bundles)

- `assets` debe listar bundles correctos (`web.assets_backend`, `web.assets_frontend`, `web.report_assets_common`, `web.assets_tests`, etc.).
- Extensiones coherentes: `.js`, `.scss`, `.css`, `.xml` (OWL templates).
- Archivos borrados deben quitarse también de `assets`.

## Hooks

- `pre_init_hook`, `post_init_hook`, `uninstall_hook`, `post_load`: si están declarados, verificar que apunten a funciones existentes en el módulo (`from . import hooks` o similar).
- Los hooks deben ser idempotentes y no dependientes de datos demo.

## Demo data

- Datos de demo en la key `demo`, **no** mezclados con `data`.
- Al introducir funcionalidad nueva que se beneficia de casos visibles, considerar agregar demo; al introducir módulo de configuración, no es necesario.
