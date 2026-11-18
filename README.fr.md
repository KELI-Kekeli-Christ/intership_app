<p align="center">
  <a href="README.md">English</a>
  &nbsp;·&nbsp;
  <a href="README.fr.md"><b>Français</b></a>
  &nbsp;·&nbsp;
  <a href="README.es.md">Español</a>
</p>

Recherche de stages. `app.py` est une API Flask. La route présente est `GET /find-internships` avec les champs `domain` et `after`. `streamlit_app.py` est un formulaire qui appelle cette API (par défaut `http://127.0.0.1:5000/find-internships`).

```bash
pip install -r requirements.txt
python app.py
streamlit run streamlit_app.py
```

---
