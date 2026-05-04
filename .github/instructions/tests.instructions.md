---
applyTo:
  - "**/tests/**/*.py"
  - "**/models/**/*.py"
  - "**/wizards/**/*.py"
  - "**/wizard/**/*.py"
  - "**/controllers/**/*.py"
---

# Revisión de cobertura de tests

## Cuándo sugerir tests

Sugerir agregar tests cuando el diff introduce **funcionalidad no trivial**:

- Métodos nuevos con lógica de negocio (cálculos, validaciones, transiciones de estado).
- Nuevos flujos/wizards completos.
- Refactors amplios de código existente (especialmente si cambia firma de métodos públicos).
- Nuevas APIs/endpoints de controladores.
- Cambios en reportes que alteran la salida.
- Overrides de `create`/`write`/`unlink` con side effects.

## Cuándo NO sugerir

- Cambios puramente cosméticos (textos, vistas simples, ajustes de estilo).
- Correcciones menores sin cambio de comportamiento.
- Solo traducciones / solo documentación.
- Renombres de variables.

## Tipo de test apropiado

- **Unitario de modelo** (`TransactionCase` / `TestCase`): validar métodos, constraints, computes, onchanges.
- **Wizard test**: instanciar wizard, setear campos, disparar acción, assert resultado.
- **HttpCase**: controladores, rutas, autenticación, respuesta.
- **Tour** (`odoo.tests.common.HttpCase` + tour JS): flujos de UI críticos, especialmente en OWL components.
- **Reporte**: generar reporte contra data conocida y comparar output.

## Calidad del test

- `setUp` preparando datos mínimos; preferir factory methods o datos de demo.
- Assertions concretas: no `assertTrue(result)` si se puede `assertEqual(result, expected)`.
- Decoradores apropiados: `@tagged('post_install', '-at_install')` para tests que dependen de módulos dependientes.
- Evitar dependencias del orden de ejecución entre tests; cada test debe ser independiente.
- Si el test crea registros con datos predecibles, usar ids/xml_ids estables para poder referenciarlos.

## Patrones a marcar como issue

- Test nuevo sin `assertEqual` / `assertRaises` / similar → no valida nada.
- `try: ... except: pass` en tests → oculta fallos.
- Tests que dependen de la hora del sistema sin `freeze_time` / `mute_logger` donde aplica.
- Tests que modifican `noupdate` records sin restaurar estado.

## Criterio de suficiencia

- No exigir una suite completa por cada cambio.
- Una sugerencia concreta y breve es suficiente: "Para este método de cálculo, podría agregarse un test unitario que cubra el caso X." (sin diseñar la suite entera).
- Si el módulo ya tiene una carpeta `tests/` con cobertura previa similar, sugerir seguir el mismo estilo.

## En PRs que SÍ agregan tests

- Verificar que el test realmente cubra el diff (no solo código alrededor).
- Que no haga mocks innecesarios del ORM (regla del equipo: preferir tests de integración sobre mocks de BD).
- Que se ejecute: nombre `test_*.py`, clase `Test*`, método `test_*`.
- `__init__.py` en `tests/` importa el nuevo archivo.
