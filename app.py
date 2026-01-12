import os
from flask import Flask, jsonify, request
from flask import render_template_string
import requests
from typing import List
from dotenv import load_dotenv
from llama_index.core import Document, SummaryIndex

load_dotenv()

app = Flask(__name__)

# Minimal OpenAPI (Swagger) spec for the existing endpoint
swagger_spec = {
    "openapi": "3.0.0",
    "info": {
        "title": "Internship Finder API",
        "version": "0.1",
        "description": "API pour rechercher des offres de stage"
    },
    "paths": {
        "/find-internships": {
            "get": {
                "summary": "Recherche des offres de stage",
                "parameters": [
                    {
                        "name": "domain",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string"},
                        "description": "Domaine recherché (ex: Data Science)"
                    },
                    {
                        "name": "after",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string", "format": "date"},
                        "description": "Date minimum (YYYY-MM-DD)"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Résultat de la recherche",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "search_summary": {"type": "string"},
                                        "raw_links": {"type": "array", "items": {"type": "object"}}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

def get_internship_dorks(keyword, site, after):
    """Interroge Serper avec un dork spécifique aux stages."""
    url = "https://google.serper.dev/search"
    # Dork optimisé pour éviter les vieux articles et cibler les offres
    full_query = f'site:{site} "{keyword}" (stage OR internship OR "alternance") after:{after}'
    
    payload = {
        "q": full_query,
        "num": 10,
        "tbs": "qdr:w"  # Force les résultats de la dernière semaine au niveau de Google
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

def generate_summary_with_gemini(doc_text: str, api_key: str) -> str:
    """Génère un résumé en utilisant l'API REST Google Gemini 1.5 Flash."""
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY est requise pour la synthèse Gemini")
    
    # URL correcte pour Gemini 1.5 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    # Structure OBLIGATOIRE pour Gemini 1.5
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"Agis en tant qu'expert en recrutement. Analyse et résume ces offres de stage de manière structurée , soit precis et concis : {doc_text}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1800  # Augmenté pour ne pas couper le résumé
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        j = resp.json()
        
        # Extraction du texte selon la hiérarchie spécifique de Gemini
        # candidates -> content -> parts -> text
        candidates = j.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return parts[0].get("text", "Aucun texte généré.")
        
        return "Format de réponse inattendu de l'API."
        
    except Exception as e:
        return f"Erreur Gemini: {str(e)}"


@app.route('/swagger.json')
def swagger_json():
        return jsonify(swagger_spec)


@app.route('/docs')
def docs():
        html = '''<!doctype html>
<html>
<head>
    <meta charset="utf-8" />
    <title>API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" />
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {
            SwaggerUIBundle({
                url: "/swagger.json",
                dom_id: '#swagger-ui',
                presets: [SwaggerUIBundle.presets.apis],
                layout: "BaseLayout"
            });
        };
    </script>
</body>
</html>'''
        return render_template_string(html)

@app.route('/find-internships', methods=['GET'])
def find_internships():
    domain = request.args.get('domain', 'Data Science')
    date_limit = request.args.get('after', '2026-01-01')
    
    # Les meilleurs sites pour les stages en France/Europe
    target_sites = [
        "linkedin.com/posts",
        "welcometothejungle.com",
        "hellowork.com",
        "jobs.lever.co", # Sites de recrutement directs (ATS)
        "greenhouse.io"   # Sites de recrutement directs (ATS)
    ]
    
    all_offers = []
    llama_docs = []

    for site in target_sites:
        results = get_internship_dorks(domain, site, date_limit)
        for res in results:
            offer = {
                "title": res.get("title"),
                "link": res.get("link"),
                "snippet": res.get("snippet"),
                "source": site
            }
            all_offers.append(offer)
            # On crée un document pour LlamaIndex
            llama_docs.append(Document(text=f"Titre: {offer['title']}\nExtrait: {offer['snippet']}\nLien: {offer['link']}"))

    # Analyse intelligente avec LlamaIndex ou fallback Gemini
    gemini_key = os.getenv("GOOGLE_API_KEY")
    if not llama_docs:
        summary = "Aucune offre récente trouvée."
    else:
        if gemini_key:
            try:
                index = SummaryIndex.from_documents(llama_docs)
                query_engine = index.as_query_engine()
                summary = query_engine.query(
                    f"Parmi ces offres pour un stage en {domain}, identifie les 5 plus pertinentes. "
                    "Donne pour chacune : l'entreprise, le rôle et pourquoi c'est une bonne opportunité."
                )
            except Exception as e:
                err = str(e)
                if gemini_key:
                        # build a simple prompt from documents
                        doc_text = "\n\n".join([d.text for d in llama_docs])
                        summary = generate_summary_with_gemini(
                            f"Parmi ces offres pour un stage en {domain}, identifie les 5 plus pertinentes. "
                            "Donne pour chacune : l'entreprise, le rôle et pourquoi c'est une bonne opportunité.\n\n" + doc_text,
                            gemini_key,
                        )
                else:
                        summary = f"Erreur lors de l'analyse IA: {err}"
      
        else:
            summary = "GEMINI_API_KEY non configurées — résumé IA désactivé."

    return jsonify({
        "search_summary": str(summary),
        "raw_links": all_offers
    })

if __name__ == '__main__':
    app.run(debug=True)