# Contributing Guidelines & Naming Conventions

## 1. Branch Protection Policy

### Protected Branches (Direct Pushes Blocked)

Die folgenden Branches sind **geschützt** und erlauben keine direkten Pushes:

- **`master`** - Produktions-Hauptbranch
  - Status: ✅ Geschützt
  - Direkte Pushes: ❌ Blockiert
  - PRs erforderlich: ✅ Ja
  - Reviewer erforderlich: ✅ Ja
  - Status Checks erforderlich: ✅ Ja (Lint, Tests)

- **`release/*`** - Release-Branches (z.B. `release/v4.1.0`, `release/v4.1.1`)
  - Status: ✅ Geschützt
  - Direkte Pushes: ❌ Blockiert
  - PRs erforderlich: ✅ Ja
  - Reviewer erforderlich: ✅ Ja
  - Status Checks erforderlich: ✅ Ja (Lint, Tests)

### Development Branches (Direkte Pushes Erlaubt)

Die folgenden Branch-Typen erlauben direkte Pushes für aktive Entwicklung:

- **`feature/*`** - Neue Features (z.B. `feature/PRO-123-login-api`)
- **`bugfix/*`** - Fehlerbehebungen (z.B. `bugfix/PRO-123-scan-timeout`)
- **`hotfix/*`** - Kritische Fehlerbehebungen (z.B. `hotfix/PRO-123-security-patch`)
- **`refactor/*`** - Code-Refactoring (z.B. `refactor/PRO-296-remaining`)
- **`docs/*`** - Dokumentationsänderungen (z.B. `docs/PRO-123-api-docs`)
- **`test/*`** - Test-Verbesserungen (z.B. `test/PRO-297-setup-verification`)

---

## 2. Branch Naming Conventions

### Standard Branch Naming
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

---

## 3. Commit Naming (Conventional Commits Standard)
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

## 4. Pull-Request Naming
- **Format:** `[Type][PRO-123] Clear description of changes`
- **Typen:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `hotfix`
- **Beschreibung:** Was wird geändert? (max. 72 Zeichen)
- **Template:** Verwende PR-Templates für konsistente Struktur

Beispiel: 
- `[feat][PRO-123] Add dashboard UI with user authentication`
- `[fix][PRO-123] Prevent MAC address spoofing vulnerability`
- `[docs][PRO-123] Update API documentation for v2.0`

## 5. Release Naming (Semantic Versioning)

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
6. Merge Release-Branch zurück zu master und develop (falls vorhanden)

## 6. Git Compatibility Rules

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

---

## 7. Git Workflow & Development Process

### Schritt-für-Schritt Anleitung für Feature-Entwicklung:

1. **Feature-Branch erstellen** (normalerweise von `master`):
   ```bash
   git checkout -b feature/PRO-123-description master
   ```

2. **Änderungen vornehmen** und mit Conventional Commits committen:
   ```bash
   git commit -m "feat(scope): description
   
   Refs: PRO-123"
   ```

3. **Zu Branch pushen**:
   ```bash
   git push origin feature/PRO-123-description
   ```

4. **Pull Request öffnen** mit entsprechendem Ziel-Branch:
   - **`master`** für Releases oder kritische Fixes
   - **`develop`** (falls vorhanden) für Feature-Entwicklung
   - Development Branches für Feature-Arbeit

5. **Auf Review und CI-Checks warten**:
   - ✅ Lint-Checks (Ruff, Black, Pydocstyle)
   - ✅ Unit-Tests bestanden
   - ✅ Code-Coverage erfüllt Standards
   - ✅ Mindestens eine Genehmigung

6. **PR mergen** nach erfolgreichen Checks und Genehmigung

### Release-Prozess:

1. **Release-Branch erstellen** von `master`:
   ```bash
   git checkout -b release/vX.Y.Z master
   ```

2. **Versionsnummern aktualisieren** und finale Commits erstellen

3. **Pull Request** öffnen mit Ziel `master`

4. **Nach Genehmigung und Merge** Git-Tag erstellen:
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

### Versuch, direkt zu geschütztem Branch zu pushen:

Wenn Sie versuchen, direkt zu einem geschützten Branch zu pushen:

```bash
$ git push origin master
remote: error: GH006: Protected branch update failed for refs/heads/master.
remote: error: You have insufficient permissions to push to this branch on this repository.
```

**Lösung:** Feature-Branch erstellen, Änderungen vornehmen und PR öffnen statt dessen.

---

## 8. GitHub Actions Workflow-Durchsetzung

Der CI/CD-Pipeline (`.github/workflows/python-ci.yml`) setzt diese Schutzmaßnahmen durch:

- ✅ Läuft nur auf Entwicklungs-Branches für `push` Events
- ✅ Läuft auf PRs zu allen Branches (einschließlich geschützter Branches)
- ✅ Test-Jobs laufen **nur** für PRs mit Ziel `master` oder `release/*`
- ✅ Deploy-Jobs laufen **nur** für PRs mit Ziel `master`

### Push Events triggern auf:
- `feature/*`, `refactor/*`, `docs/*`, `test/*`, `bugfix/*`, `hotfix/*`

### PR Events triggern auf:
- Alle Ziel-Branches (`master`, `release/*`, Entwicklungs-Branches)

### Workflow-Modell für geschützte Branches:

```
Geschützter Branch (master/release/*)
    ↑
    │ PR erforderlich
    │ (Lint-Checks + Tests)
    │
Development Branch
    ↓ direkter Push erlaubt
    ↓ (nur Lint-Checks)
```

---

## 9. Code Quality Requirements

Alle PRs müssen diese Anforderungen erfüllen:

### 1. Lint-Checks:
- ✅ **Ruff** - Python Linter
- ✅ **Black** - Code Formatter
- ✅ **Pydocstyle** - Docstring Validator
- ✅ **Radon** - Complexity Analyzer

### 2. Testing:
- ✅ Alle Unit-Tests bestanden
- ✅ Code-Coverage beibehalten

### 3. Review:
- ✅ Mindestens eine Genehmigung
- ✅ Keine ausstehenden Review-Anfragen

---

## 10. Schnelle Referenz

| Typ | Branch | PR-Titel | Commit | Geschützt |
|-----|--------|---------|--------|-----------|
| Feature | `feature/PRO-123-desc` | `[feat][PRO-123] Description` | `feat(scope): desc` | ❌ |
| Bugfix | `bugfix/PRO-123-desc` | `[fix][PRO-123] Description` | `fix(scope): desc` | ❌ |
| Hotfix | `hotfix/PRO-123-desc` | `[hotfix][PRO-123] Description` | `fix(scope): desc` | ❌ |
| Refactor | `refactor/PRO-123-desc` | `[refactor][PRO-123] Description` | `refactor(scope): desc` | ❌ |
| Docs | `docs/PRO-123-desc` | `[docs][PRO-123] Description` | `docs(scope): desc` | ❌ |
| Test | `test/PRO-123-desc` | `[test][PRO-123] Description` | `test(scope): desc` | ❌ |
| Release | `release/vX.Y.Z` | `[release][PRO-123] vX.Y.Z` | `chore(release): vX.Y.Z` | ✅ |
| Main | `master` | N/A | N/A | ✅ |

---

## 11. Weitere Ressourcen

- **Branch Protection Settings**: GitHub Repository Settings → Branches → Branch Protection Rules
- **GitHub Actions Workflow**: `.github/workflows/python-ci.yml`
- **Conventional Commits**: https://www.conventionalcommits.org/
- **Semantic Versioning**: https://semver.org/

