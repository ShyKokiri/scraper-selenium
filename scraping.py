from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import csv

BASE_URL = "https://www.cassems.com.br/noticias/{}"
BASE_DOMAIN = "https://www.cassems.com.br"

class NewsDriver:
    """Classe para gerenciar o driver do Selenium"""
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(options=options)
    
    def get_soup(self, url, wait_class=None):
        try:
            self.driver.get(url)
            
            if wait_class:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, wait_class))
                )
            else:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            
            time.sleep(1)
            return BeautifulSoup(self.driver.page_source, 'html.parser')
            
        except Exception as e:
            print(f"    ⚠️ Erro ao carregar: {e}")
            return None
    
    def close(self):
        self.driver.quit()

def parse_news_content(driver, url):
    full_url = BASE_DOMAIN + url if url.startswith('/') else url
    
    soup = driver.get_soup(full_url)
    
    content = {
        "date": "N/A",
        "content": "N/A",
        "author": "N/A"
    }
    
    if not soup:
        return content
    
    date_author_tag = soup.find("small") or soup.find(string=lambda text: "Por -" in str(text) if text else False)
    
    if date_author_tag:
        text = date_author_tag.get_text(strip=True) if hasattr(date_author_tag, 'get_text') else str(date_author_tag)
        
        # Separa data e autor
        if "Por -" in text:
            parts = text.split("Por -")
            content["date"] = parts[0].strip()
            content["author"] = parts[1].strip() if len(parts) > 1 else "N/A"
        else:
            content["date"] = text
    
    # Pega o conteúdo - está no atributo ng-bind-html="noticia.texto"
    content_tag = soup.find("p", {"ng-bind-html": "noticia.texto"})
    
    if content_tag:
        # Remove tags indesejadas
        for tag in content_tag.select("script, style"):
            tag.decompose()
        
        # Pega todo o texto
        text = content_tag.get_text(strip=True, separator="\n\n")
        if text:
            content["content"] = text
    
    # Se não encontrou pelo ng-bind-html, tenta pegar todos os <p> da página
    if content["content"] == "N/A":
        paragraphs = soup.find_all("p")
        text_parts = []
        
        for p in paragraphs:
            text = p.get_text(strip=True)
            # Ignora parágrafos muito curtos ou que parecem ser menus/navegação
            if text and len(text) > 50 and "Por -" not in text:
                text_parts.append(text)
        
        if text_parts:
            content["content"] = "\n\n".join(text_parts)
    
    return content

def parse_news_list(driver, soup):
    results = []
    
    cards = soup.select("div.list-news")
    print(f"Cards encontrados: {len(cards)}")
    
    for i, card in enumerate(cards, 1):
        link_tag = card.find("a", href=True)
        
        if link_tag:
            link = link_tag["href"]
            
            title_tag = card.find("h5")
            title = title_tag.get_text(strip=True) if title_tag else "Sem título"

            news_data = {
                "title": title,
                "link": link
            }

            print(f"  [{i}/{len(cards)}] {title[:50]}...")
            news_content = parse_news_content(driver, link)
            
            if news_content:
                news_data.update(news_content)
            
            results.append(news_data)
            time.sleep(0.3) 

    return results

def scrape_pages(start=1, end=10, delay=1):
    all_news = []
    driver = NewsDriver() 
    
    try:
        for page in range(start, end + 1):
            print(f"\n{'='*60}")
            print(f"📰 PÁGINA {page}/{end}")
            print(f"{'='*60}")
            
            url = BASE_URL.format(page)
            soup = driver.get_soup(url, wait_class="list-news")

            if soup:
                page_news = parse_news_list(driver, soup)
                print(f"\n✓ {len(page_news)} notícias coletadas")
                all_news.extend(page_news)
            else:
                print(f"✗ Erro ao carregar página {page}")

            time.sleep(delay)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
    finally:
        print("\n🔒 Fechando driver...")
        driver.close()

    return all_news

def save_csv(data, filename="noticias.csv"):
    if not data:
        print("Nenhum dado para salvar!")
        return
    
    keys = data[0].keys()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"\n✅ Arquivo salvo: {filename}")

if __name__ == "__main__":
    # Teste com poucas páginas primeiro
    noticias = scrape_pages(start=1, end=185, delay=1)
    
    if noticias:
        save_csv(noticias)
        
        print(f"\n{'='*60}")
        print(f"📊 TOTAL: {len(noticias)} notícias coletadas")
        print(f"{'='*60}\n")
        
        # Mostra exemplo da primeira notícia
        print("📄 Exemplo da primeira notícia:\n")
        print(f"Título: {noticias[0]['title']}")
        print(f"Link: {noticias[0]['link']}")
        print(f"Data: {noticias[0].get('date', 'N/A')}")
        print(f"Autor: {noticias[0].get('author', 'N/A')}")
        print(f"Conteúdo: {noticias[0].get('content', 'N/A')}...")