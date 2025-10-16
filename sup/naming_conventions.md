# Naming Conventions für SecurityAdvisor

## Branch Naming
- **<typ>-PRO-Nummer/<kurzbeschreibung>**: Neue Features
- **feature/<kurzbeschreibung>**: Neue Features
- **bugfix/<kurzbeschreibung>**: Fehlerbehebungen
- **hotfix/<kurzbeschreibung>**: Kritische Fehlerbehebungen
- **refactor/<kurzbeschreibung>**: Refactoring
- **docs/<kurzbeschreibung>**: Dokumentationsänderungen
- **test/<kurzbeschreibung>**: Test-Verbesserungen
- **release/<version>**: Release-Vorbereitung

Beispiel: `feature/PRO-123:login-api`, `bugfix/PRO-123:scan-timeout`, `release/v1.2.0`

## Commit Naming
- **<Typ>/PRO-Nummer: <kurze Beschreibung>**
- Typen: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`
- Beschreibung: Klar, prägnant, im Imperativ

Beispiel: `feat/PRO-123: add device scan`, `fix/PRO-123: resolve VPN config bug`

## Pull-Request Naming
- **[Typ][PRO-Nummer] <kurze Beschreibung>**
- Typen wie bei Commits
- Beschreibung: Was wird geändert?

Beispiel: `[feat][PRO-123] Add dashboard UI`, `[fix][PRO-123] Prevent MAC spoofing`

## Release Naming

### Release Naming Convention
- **Format:** `vxx.yy.zz`
	- **xx**: MAJOR version – wird erhöht bei inkompatiblen API-Änderungen
	- **yy**: MINOR version – wird erhöht bei neuen, abwärtskompatiblen Features
	- **zz**: PATCH version – wird erhöht bei abwärtskompatiblen Bugfixes
- **Beispiel:** `v02.01.02`

### JIRA Ticket Referenz
	- Für jede Release, Branch, Commit und Pull-Request muss die JIRA Ticketnummer (z.B. `PRO-123`) enthalten sein.
	- Beispiel Branch: `feature/PRO-123-login-api`
	- Beispiel Commit: `feat/PRO-123: add device scan`
	- Beispiel PR: `[feat][PRO-123] Add dashboard UI`
	- Beispiel Release: `v02.01.02-PRO-123`

**Hinweis:**
Die JIRA Ticketnummer (Initialien PRO-Nummer) ist grundlegend für das Projekt und sollte immer zur Nachverfolgbarkeit und automatischen Verknüpfung mit JIRA verwendet werden.
