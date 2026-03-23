# API Tester PRO (Python/Tkinter)

Versión pro:
- Endpoints desde `routers.zip` (parseo de routers FastAPI)
- **OpenAPI** desde `/openapi.json` para:
  - Precargar **Body JSON** según `requestBody.schema`
  - Precargar **params** según `parameters`
  - Sugerir **auth headers** según `securitySchemes`

## Instalar y ejecutar
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python app_gui.py
```

## Uso
1) Seteá Base URL
2) Sincronizar OpenAPI
3) (Opcional) cargar routers.zip
4) Seleccionar endpoint → autocompleta
