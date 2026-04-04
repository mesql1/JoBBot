import requests
import os
from dotenv import load_dotenv
import re

load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env

def limpar_html(texto):
    # Remove tags HTML usando expressões regulares
    if not texto:
        return "N/A"
    return re.sub('<[^<]+?>', '', texto)

def buscar_vagasOnline(termo="TI"):
    APP_ID=os.getenv('ADZUNA_ID')
    APP_KEY=os.getenv('ADZUNA_KEY')
    PAIS='br'

    url=f"https://api.adzuna.com/v1/api/jobs/{PAIS}/search/1"
    
    params={
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "results_per_page": 10,
        "what": termo,
        'content-type': 'application/json'
    }
    
    try:
        response=requests.get(url, params=params)
        response.raise_for_status()  # Verifica se a requisição foi bem-sucedida
        dados=response.json()
        vagas=dados.get("results", [])

        vagas_formatadas=[]# Lista para armazenar as vagas formatadas
        for vaga in vagas:
            vagas_formatadas.append({
                "titulo": limpar_html(vaga.get("title", "N/A")),
                "empresa": limpar_html(vaga.get("company", {}).get("display_name", "N/A")),# Acessa o nome da empresa, garantindo que o campo exista
                "localizacao": limpar_html(vaga.get("location", {}).get("display_name", "N/A")),# Acessa a localização, garantindo que o campo exista
                "area": termo,
                "link": vaga.get("redirect_url", "N/A")
            })
    
        return vagas_formatadas
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar vagas: {e}")
        return []