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
dotnet test -c Release tests/localization/SRALocalizationChecks.csproj
```

Runs as a normal xUnit project (`dotnet test --filter` works as usual). The cases cover
compiled Russian satellite resources, culture selection, explicit-fixture JSON language
persistence, formatted messages, numeric extension enums, and the actual
`LocalBackendService` three-pipe UTF-8 contract against an echo-only Python fixture.
`ViewRenderingTests` renders real Avalonia settings, console, Currency Wars and extension
views in a headless SukiUI host at 800/1024 pixels in light/dark mode and all three
languages, and verifies that UI language selection preserves the runtime parsing culture,
long Russian settings labels wrap, and console filter labels fit their line height.

Avalonia only allows one UI thread, so `AvaloniaSession` starts a dedicated thread that
does `SetupWithoutStarting` and runs the dispatcher loop; every UI assertion is dispatched
there. All tests are serialized because `Resources.Culture`, `SukiTheme` and
`RequestedThemeVariant` are process-wide state.

Environment variables:

- `SRA_TEST_PYTHON` — Python 3.12 interpreter for the pipe test. When unset, `py -3.12`
  and `python` are probed; the case fails with a hint if none is found.
- `SRA_TEST_OUTPUT` — screenshot directory (48 PNGs). Defaults to
  `%TEMP%/sra-localization-checks`; do not commit them.

It deliberately does **not** run `App.OnFrameworkInitializationCompleted`,
`SettingsService.Load`, registry access, updater, network services or backend CLI
tasks. Settings/task pages have no runtime data context; the extension form uses
synthetic fields. This is a resource/layout smoke test, not a full interactive
desktop acceptance test.

WebUI resource and locale tests are in
`SRAFrontend/srafrontend-webui/src/utils/__tests__/localization.spec.ts` and run
with the existing `pnpm test` command.
