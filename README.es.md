<p align="center">
  <a href="README.md">English</a>
  &nbsp;·&nbsp;
  <a href="README.fr.md">Français</a>
  &nbsp;·&nbsp;
  <a href="README.es.md"><b>Español</b></a>
</p>

Búsqueda de prácticas. `app.py` es una API Flask. La ruta que existe es `GET /find-internships` con los campos `domain` y `after`. `streamlit_app.py` es un formulario que llama a esa API (por defecto `http://127.0.0.1:5000/find-internships`).

```bash
pip install -r requirements.txt
python app.py
streamlit run streamlit_app.py
```

---
