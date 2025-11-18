# Naming Conventions für SecurityAdvisor

## Branch Naming
- **feature/PRO-123-description**: Neue Features
- **bugfix/PRO-123-description**: Fehlerbehebungen
- **hotfix/PRO-123-description**: Kritische Fehlerbehebungen
- **refactor/PRO-123-description**: Refactoring
- **docs/PRO-123-description**: Dokumentationsänderungen
- **test/PRO-123-description**: Test-Verbesserungen
- **release/vX.Y.Z**: Release-Vorbereitung

### Branch Naming Rules:
- Nur Kleinbuchstaben, Zahlen, Bindestriche und Schrägstriche
- Keine Leerzeichen, Doppelpunkte, Pipes oder Sonderzeichen
- Maximale Länge: 50 Zeichen
- Format: `typ/PRO-123-kurze-beschreibung`

Beispiel: `feature/PRO-123-login-api`, `bugfix/PRO-123-scan-timeout`, `release/v1.2.0`

## Commit Naming (Conventional Commits Standard)
- **Format:** `type(scope): description`
- **Typen:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`, `ci`, `build`
- **Beschreibung:** Klar, prägnant, im Imperativ (max. 50 Zeichen)
- **Footer:** JIRA-Referenz: `Refs: PRO-123`

### Commit Format:
```
type(scope): subject line

Optional body explaining the change in more detail.

Refs: PRO-123
```

Beispiel: 
- `feat(auth):add device scan functionality`
- `fix(vpn):resolve connection timeout issue`
- `docs(api):update authentication guide`

## Pull-Request Naming
- **Format:** `[Type][PRO-123] Clear description of changes`
- **Typen:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `hotfix`
- **Beschreibung:** Was wird geändert? (max. 72 Zeichen)
- **Template:** Verwende PR-Templates für konsistente Struktur

Beispiel: 
- `[feat][PRO-123] Add dashboard UI with user authentication`
- `[fix][PRO-123] Prevent MAC address spoofing vulnerability`
- `[docs][PRO-123] Update API documentation for v2.0`

## Release Naming (Semantic Versioning)

### Release Naming Convention
- **Format:** `vX.Y.Z` (ohne führende Nullen)
  - **X**: MAJOR version – inkompatible API-Änderungen
  - **Y**: MINOR version – neue, abwärtskompatible Features
  - **Z**: PATCH version – abwärtskompatible Bugfixes
- **Beispiel:** `v1.2.3`, `v2.0.0`, `v1.4.7`

### Release-Branches:
- **Format:** `release/vX.Y.Z`
- **Zweck:** Stabilisierung und Vorbereitung vor dem Release
- **Nachbenennung:** Nach Release werden RC-Branches in `release/vX.Y.Z` Format umbenannt
- **Beispiel:** `release/v4.1.0`, `release/v4.1.1`, `release/v2.0.0`

### Release-Tags:
- **Format:** `vX.Y.Z` (Semantic Versioning)
- **Zweck:** Markierung von offiziellen, stabilen Releases
- **Zuordnung:** Jeder `release/vX.Y.Z` Branch erhält einen entsprechenden `vX.Y.Z` Tag
- **Erstellung:** Tag wird auf dem finalen Commit des Release-Branches erstellt
- **Beispiel:** `v4.1.0`, `v4.1.1`, `v2.0.0`

### Historische Versioning (Legacy):
- Tags im Format `RX.Y.Z` (z.B. `R04.01.00`, `R03.00.00`) werden beibehalten für Rückverfolgbarkeit
- Neue Releases verwenden ausschließlich `vX.Y.Z` Format mit entsprechenden `release/vX.Y.Z` Branches

### Release-Workflow:
1. Erstelle Release-Branch: `git checkout -b release/vX.Y.Z develop` (oder main/master)
2. Bump Version in relevanten Dateien (z.B. README.md, Versionsnummern)
3. Erstelle finalen Commit mit Release-Notes
4. Erstelle Tag: `git tag vX.Y.Z`
5. Push beides zu Origin: `git push origin release/vX.Y.Z` und `git push origin vX.Y.Z`
6. Merge Release-Branch zurück zu master

## Git Compatibility Rules

### Verbotene Zeichen in Branch-Namen:
- Pipe (`|`), Doppelpunkt (`:`), Fragezeichen (`?`)
- Sterne (`*`), eckige Klammern (`[]`), Backslash (`\`)
- Kleiner/Größer (`<>`), Anführungszeichen (`"`), At (`@`)
- Geschweifte Klammern (`{}`), Tilde (`~`)

### Erlaubte Zeichen:
- Kleinbuchstaben (a-z)
- Zahlen (0-9)
- Bindestriche (-) - nicht am Anfang oder Ende
- Schrägstriche (/) - als Trennzeichen zwischen Typ und Name

### Windows-Kompatibilität:
- Keine reservierten Namen: CON, PRN, AUX, NUL, COM1-9, LPT1-9
- Maximale Pfadlänge beachten (260 Zeichen)

### JIRA Ticket Referenz
- Für jede Release, Branch, Commit und Pull-Request muss die JIRA Ticketnummer enthalten sein
- **Branch:** Ticketnummer im Namen: `feature/PRO-123-description`
- **Commit:** Ticketnummer im Footer: `Refs: PRO-123`
- **PR:** Ticketnummer im Titel: `[feat][PRO-123] Description`
- **Release:** Ticketnummer in Release Notes verlinken

Beispiele:
- Branch: `feature/PRO-123-user-authentication`
- Commit: `feat(auth): add login validation\n\nRefs: PRO-123`
- PR: `[feat][PRO-123] Implement user authentication system`
- Release: `v1.2.0` (mit PRO-123 in Release Notes)

**Hinweis:**
Die JIRA Ticketnummer (Initialien PRO-Nummer) ist grundlegend für das Projekt und sollte immer zur Nachverfolgbarkeit und automatischen Verknüpfung mit JIRA verwendet werden.

### Arbeiten ohne JIRA Ticket
Falls kein JIRA Ticket verfügbar ist, sollten Branches, Commits und Pull-Requests im Format `type/description` ohne PRO-XXX erstellt werden:
- **Branch:** `type/description` (z.B. `feature/user-login`, `refactor/timesheet-2025-update`)
- **Commit:** Normale Conventional Commits ohne `Refs: PRO-XXX` Footer
- **PR:** `[Type] Description` ohne Ticketnummer (z.B. `[feat] Add user login functionality`)

**Wichtig:** Sobald ein JIRA Ticket verfügbar ist, sollte die Referenz nachträglich hinzugefügt werden.
