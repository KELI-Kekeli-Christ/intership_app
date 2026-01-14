import os
import json
from flask import Flask, jsonify, request, render_template_string
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- OpenAPI Spec ---
swagger_spec = {
    "openapi": "3.0.0",
    "info": {
        "title": "Internship Finder API",
        "version": "0.4",
        "description": "API améliorée : Gestion flexible des domaines et mots-clés."
    },
    "paths": {
        "/find-internships": {
            "get": {
                "summary": "Recherche des offres",
                "parameters": [
                    {"name": "domain", "in": "query", "required": False, "schema": {"type": "string"}},
                    {"name": "keywords", "in": "query", "required": False, "schema": {"type": "string"}},
                    {"name": "city", "in": "query", "required": False, "schema": {"type": "string"}},
                    {"name": "company", "in": "query", "required": False, "schema": {"type": "string"}},
                    {"name": "after", "in": "query", "required": False, "schema": {"type": "string", "format": "date"}}
                ],
                "responses": {
                    "200": {
                        "description": "Résultat structuré",
                        "content": {"application/json": {}}
                    }
                }
            }
        }
    }
}


def get_internship_dorks(domain, keywords, city, company, site, after):
    """Interroge Serper avec des filtres intelligents."""
    url = "https://google.serper.dev/search"

    query_parts = [f'site:{site}']

    # --- CORRECTION ICI ---
    # On ajoute le domaine SEULEMENT s'il contient du texte
    if domain and domain.strip():
        query_parts.append(f'"{domain}"')

    # On ajoute les mots-clés SEULEMENT s'ils contiennent du texte
    if keywords and keywords.strip():
        query_parts.append(f'{keywords}')

    if company and company.strip():
        query_parts.append(f'"{company}"')

    if city and city.strip():
        query_parts.append(f'"{city}"')

    query_parts.append('(stage OR internship OR "alternance")')
    query_parts.append(f'after:{after}')

    # Sécurité : Si la requête est trop vide (ni domaine, ni keyword, ni boite), on évite de chercher
    # Cela évite de faire une recherche "site:linkedin.com (stage)" trop générique qui gaspille des crédits
    relevant_terms = [domain, keywords, company]
    if not any(t and t.strip() for t in relevant_terms):
        return []

    payload = {
        "q": " ".join(query_parts),
        "num": 10,
        "tbs": "qdr:m"
    }
    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json().get("organic", [])
    except:
        return []


def clean_title_extraction(title):
    """Tentative simple d'extraire l'entreprise du titre via Python (Fallback)."""
    separators = [' - ', ' | ', ' : ', ' chez ', ' at ']
    for sep in separators:
        if sep in title:
            parts = title.split(sep)
            if len(parts) > 1:
                return parts[1].strip()
    return "Non détecté"


def structure_offers_with_gemini(raw_offers_text: str, api_key: str):
    """Utilise Gemini pour structurer les données."""
    if not api_key:
        return []

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    prompt = (
        "Tu es un expert en extraction de données (Data Parsing). "
        "Je vais te donner une liste d'offres de stage brutes. "
        "Tu dois remplir les champs 'Entreprise', 'Ville' et 'Durée'."
        "\n\nRÈGLES :"
        "\n1. ENTREPRISE : Trouve le nom de l'entreprise dans le titre ou le snippet. Si introuvable, mets 'Inconnu'."
        "\n2. VILLE : Trouve la ville (ex: Paris, Lyon) ou le pays. Si introuvable, mets 'France / Télétravail'."
        "\n3. DURÉE : Cherche la durée (ex: 6 mois). Sinon mets 'Non spécifié'."
        "\n\nDonnées brutes :\n"
        f"{raw_offers_text}"
        "\n\nRenvoie UNIQUEMENT une liste JSON valide [ {...}, {...} ] sans Markdown."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=40)
        resp.raise_for_status()
        j = resp.json()
        text_resp = j['candidates'][0]['content']['parts'][0]['text']
        clean_json = text_resp.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"Erreur Extraction Gemini: {e}")
        return []


@app.route('/swagger.json')
def swagger_json():
    return jsonify(swagger_spec)


@app.route('/docs')
def docs():
    html = '''<!doctype html><html><head><title>API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" /></head>
    <body><div id="swagger-ui"></div><script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
    <script>window.onload = function() {SwaggerUIBundle({url: "/swagger.json", dom_id: '#swagger-ui', presets: [SwaggerUIBundle.presets.apis], layout: "BaseLayout"});};</script>
    </body></html>'''
    return render_template_string(html)


@app.route('/find-internships', methods=['GET'])
def find_internships():
    # --- CORRECTION ICI ---
    # On utilise .get() simplement. Si l'utilisateur envoie ?domain= (vide),
    # la variable domain sera "" (vide). C'est ce qu'on veut pour nos tests plus bas.
    domain = request.args.get('domain', '')
    keywords = request.args.get('keywords', '')
    city = request.args.get('city', '')
    company = request.args.get('company', '')
    date_limit = request.args.get('after', '2026-01-01')

    target_sites = [
        "linkedin.com/posts",
        "welcometothejungle.com",
        "hellowork.com",
        "jobs.lever.co",
        "greenhouse.io"
    ]

    all_raw_offers = []

    # 1. Collecte Serper
    for site in target_sites:
        results = get_internship_dorks(domain, keywords, city, company, site, date_limit)
        for res in results:
            all_raw_offers.append({
                "title": res.get("title"),
                "link": res.get("link"),
                "snippet": res.get("snippet"),
                "source": site
            })

    gemini_key = os.getenv("GOOGLE_API_KEY")
    structured_results = []
    summary = ""

    if all_raw_offers:
        # 2. Extraction IA
        if gemini_key:
            offers_text_block = json.dumps(all_raw_offers, ensure_ascii=False)
            structured_data = structure_offers_with_gemini(offers_text_block, gemini_key)

            if structured_data:
                for item in structured_data:
                    structured_results.append({
                        "Title": item.get('Title', 'Sans titre'),
                        "Durée": item.get('Durée', 'Non spécifié'),
                        "Entreprise": item.get('Entreprise', 'Non spécifié'),
                        "Ville": item.get('Ville', 'Non spécifié'),
                        "Snippet": item.get('Snippet', ''),
                        "Link": item.get('Link', '#')
                    })
                summary = f"{len(structured_results)} offres structurées par l'IA."
            else:
                for offer in all_raw_offers:
                    guessed_company = clean_title_extraction(offer['title'])
                    structured_results.append({
                        "Title": offer['title'],
                        "Durée": "À vérifier",
                        "Entreprise": company if company else guessed_company,
                        "Ville": city if city else "Voir détail",
                        "Snippet": offer['snippet'],
                        "Link": offer['link']
                    })
                summary = "Extraction basique (IA indisponible)."
        else:
            summary = "Mode sans IA."
            for offer in all_raw_offers:
                structured_results.append({
                    "Title": offer['title'],
                    "Durée": "-", "Entreprise": "-", "Ville": "-",
                    "Snippet": offer['snippet'], "Link": offer['link']
                })

    return jsonify({
        "search_summary": summary,
        "raw_links": structured_results
    })


if __name__ == '__main__':
    app.run(debug=True)