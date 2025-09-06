# BertiBox Test Suite

Umfassende Testsuite für das BertiBox-Projekt mit Unit- und Integrationstests.

## Übersicht

Die Testsuite deckt alle wichtigen Komponenten des BertiBox-Systems ab:

- **Core Module**: Player-Funktionalität und RFID-Handling
- **Database Layer**: Models und Manager
- **API Endpoints**: REST API für Tags, Playlists, Media, Player und Upload
- **WebSocket**: Echtzeit-Kommunikation
- **Utils**: Hilfsfunktionen

## Installation

```bash
# Virtuelle Umgebung aktivieren
source venv/bin/activate

# Test-Abhängigkeiten installieren
pip install -r test_requirements.txt
```

## Tests ausführen

### Alle Tests
```bash
# Mit Make
make test

# Direkt mit pytest
python -m pytest tests/
```

### Spezifische Testmodule
```bash
# Core Player Tests
make test-core

# Database Tests
make test-database

# API Tests
make test-api

# WebSocket Tests
make test-websocket

# Utils Tests
make test-utils
```

### Einzelne Testdatei
```bash
python -m pytest tests/test_core_player.py -v
```

### Einzelner Test
```bash
python -m pytest tests/test_database_models.py::TestDatabaseModels::test_tag_creation -v
```

### Mit Coverage Report
```bash
# Installation von Coverage-Tools
pip install pytest-cov

# Tests mit Coverage ausführen
python -m pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

# HTML-Report öffnen
open htmlcov/index.html
```

## Teststruktur

```
tests/
├── __init__.py                    # Test-Package
├── test_core_player.py           # Tests für BertiBox Player
├── test_database_models.py       # Tests für DB Models
├── test_database_manager.py      # Tests für DB Manager
├── test_api_tags.py              # Tests für Tags API
├── test_api_playlists.py         # Tests für Playlists API
├── test_api_media.py             # Tests für Media Explorer API
├── test_api_player.py            # Tests für Player Control API
├── test_api_upload.py            # Tests für Upload API
├── test_websocket_handlers.py    # Tests für WebSocket Events
└── test_utils_helpers.py         # Tests für Hilfsfunktionen
```

## Test-Marker

Tests können mit Markern kategorisiert werden:

```python
@pytest.mark.unit          # Unit Tests
@pytest.mark.integration   # Integrationstests
@pytest.mark.slow          # Langsame Tests
@pytest.mark.api           # API Tests
@pytest.mark.websocket     # WebSocket Tests
@pytest.mark.database      # Database Tests
@pytest.mark.player        # Player Tests
```

Ausführung nach Marker:
```bash
# Nur Unit Tests
python -m pytest tests/ -m unit

# Nur API Tests
python -m pytest tests/ -m api
```

## Testabdeckung

Die Testsuite zielt auf eine hohe Testabdeckung ab:

- **Core/Player**: Vollständige Abdeckung der Player-Logik, RFID-Handling, Playlist-Management
- **Database**: Alle CRUD-Operationen, Beziehungen, Constraints
- **API**: Alle Endpoints mit Success- und Error-Cases
- **WebSocket**: Event-Handling und Broadcasting
- **Utils**: Validierung, Sanitization, Formatierung

## Mocking

Die Tests verwenden extensive Mocks für externe Abhängigkeiten:

- `pygame`: Audio-Playback
- `RPi.GPIO`: Hardware-Interfaces
- `MFRC522`: RFID-Reader
- Filesystem-Operationen
- Database-Sessions

## Continuous Testing

Während der Entwicklung:
```bash
# Tests bei Dateiänderungen automatisch ausführen
pip install pytest-watch
ptw tests/
```

## Troubleshooting

### Import-Fehler
```bash
# PYTHONPATH setzen
export PYTHONPATH=$PYTHONPATH:/home/jakob/git/BertiBox
```

### Mock-Probleme
```bash
# Mock-Library aktualisieren
pip install --upgrade pytest-mock
```

### Coverage nicht gefunden
```bash
# Coverage-Tools installieren
pip install pytest-cov coverage
```

## Best Practices

1. **Isolation**: Jeder Test sollte unabhängig laufen
2. **Mocking**: Externe Abhängigkeiten immer mocken
3. **Assertions**: Klare und spezifische Assertions verwenden
4. **Naming**: Beschreibende Testnamen verwenden
5. **Setup/Teardown**: Ressourcen ordnungsgemäß verwalten
6. **Coverage**: Mindestens 80% Testabdeckung anstreben

## Nützliche Befehle

```bash
# Fehlgeschlagene Tests erneut ausführen
python -m pytest tests/ --lf

# Verbose Output mit Details
python -m pytest tests/ -vv

# Nur geänderte Files testen (benötigt pytest-testmon)
pip install pytest-testmon
python -m pytest tests/ --testmon

# Parallele Ausführung (benötigt pytest-xdist)
pip install pytest-xdist
python -m pytest tests/ -n auto
```