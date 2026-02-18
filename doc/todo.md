# TODO: Exchange Rules Processing

## Status
- Analyzed `УТВыгрузитьПравила.epf`.
- Unpacked structure exists in `ПравилаОбмена/УТВыгрузитьПравила`.
- Designed improvements for file dialogs and BSP independence.
- **IMPORTANT**: Code changes were generated but NOT applied to the original files yet.

## Pending Actions
1. **Apply Code Changes**:
   - Update `Forms/Форма/Ext/Form.xml`: Add `StartChoice` events to `ИмяВременногоКаталога` and `ИмяФайлаПравил`.
   - Update `Forms/Форма/Ext/Form/Module.bsl`: Replace logic with the new implementation (dynamic BSP check, file dialogs).
   - *Reference*: See `proposed_changes_module.bsl` (I will create this).

2. **Pack Processing**:
   - Use `v8unpack` or equivalent to pack `ПравилаОбмена/УТВыгрузитьПравила` folder into `.epf`.

3. **Verify**:
   - Test in 1C Enterprise (BSP and non-BSP configurations).