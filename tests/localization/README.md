# Localization checks

These tests never start the desktop application, a game, an operator, or a task.
Do not use a production SRA installation or its settings as a test fixture.

## Python

With Python 3.12 and the project's test dependencies, run from the repository root:

```sh
python -m pytest tests/test_russian_localization.py tests/test_standard_io_utf8.py
```

The subprocess tests use temporary settings and only query CLI metadata/help.
They check all three languages, resource/placeholder parity, schema display labels
without changing aliases/enums/defaults, persisted language loading, and UTF-8
under CP1251, CP1252 and GBK. The existing main/notification tests also run offline.

## .NET / Avalonia

With .NET 10 and the normal desktop dependencies:

```sh
dotnet run -c Release --project tests/localization/SRALocalizationChecks.csproj -- <repository-root> <new-output-directory> <python-3.12-executable>
```

This small assertion runner tests compiled Russian satellite resources, culture
selection, explicit-fixture JSON language persistence, source-text normalization,
formatted messages, numeric extension enums and the actual `LocalBackendService`
three-pipe UTF-8 contract against an echo-only Python fixture. It then renders
real Avalonia settings, console, Currency Wars and extension views in a headless
SukiUI host at 800/1024 pixels in light/dark mode and all three languages.
It also verifies that UI language selection preserves the runtime parsing culture,
long Russian settings labels wrap, and console filter labels fit their line height.

It deliberately does **not** run `App.OnFrameworkInitializationCompleted`,
`SettingsService.Load`, registry access, updater, network services or backend CLI
tasks. Settings/task pages have no runtime data context; the extension form uses
synthetic fields. This is a resource/layout smoke test, not a full interactive
desktop acceptance test. Screenshots and `result.json` go only to the given output
directory; do not commit them.

WebUI resource and locale tests are in
`SRAFrontend/srafrontend-webui/src/utils/__tests__/localization.spec.ts` and run
with the existing `pnpm test` command.
