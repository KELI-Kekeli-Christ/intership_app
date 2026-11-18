<p align="center">
  <a href="README.md"><b>English</b></a>
  &nbsp;·&nbsp;
  <a href="README.fr.md">Français</a>
  &nbsp;·&nbsp;
  <a href="README.es.md">Español</a>
</p>

Internship search. `app.py` is a Flask API. The route that exists is `GET /find-internships` with query fields `domain` and `after`. `streamlit_app.py` is a form that calls that API (default `http://127.0.0.1:5000/find-internships`).

```bash
pip install -r requirements.txt
python app.py
streamlit run streamlit_app.py
```

---
