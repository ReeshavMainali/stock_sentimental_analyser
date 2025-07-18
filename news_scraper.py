import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from urllib.parse import quote
import time

class NepseNewsScraper:
    def __init__(self):
        self.base_urls = [
            "https://www.investopaper.com/?s={symbol}"
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)

    def scrape_full_article(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            article_content = soup.find('div', class_='entry-content')
            if not article_content:
                return "Full article content not found"
            
            # Remove unwanted elements
            for element in article_content.find_all(['div', 'script', 'style', 'aside', 'pre', 'hr']):
                element.decompose()
                
            # Remove social media buttons
            for element in article_content.find_all(class_=['sfsiaftrpstwpr', 'sfsi_responsive_icons']):
                element.decompose()
                
            # Remove recommended links
            for element in article_content.find_all('p'):
                if element.find('strong') and 'Recommended' in element.get_text():
                    for sibling in element.find_next_siblings():
                        if sibling.name == 'hr':
                            break
                        sibling.decompose()
                    element.decompose()
                    break
            
            # Clean paragraphs
            paragraphs = []
            for p in article_content.find_all('p'):
                text = p.get_text(strip=True)
                if text and not text.startswith(('©', 'License:', 'Author:')):
                    paragraphs.append(text)
            
            return '\n\n'.join(paragraphs) if paragraphs else "No readable content found"
            
        except Exception as e:
            print(f"Error scraping full article from {url}: {e}")
            return "Error retrieving full article content"

    def scrape_news(self, symbol):
        news_items = []
        
        for url_template in self.base_urls:
            try:
                url = url_template.format(symbol=quote(symbol))
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                article_container = soup.find('div', class_='article-container')
                if not article_container:
                    continue
                
                articles = article_container.find_all('article')
                for article in articles:
                    try:
                        title_element = article.find('h2', class_='entry-title')
                        title = title_element.get_text(strip=True) if title_element else "No title"
                        link = title_element.find('a')['href'] if title_element and title_element.find('a') else "#"
                        
                        if link == "#":
                            continue
                            
                        date_element = article.find('div', class_='entry-content').find('p')
                        date_text = date_element.get_text(strip=True).split('|')[0].strip() if date_element else "Unknown date"
                        
                        summary = ""
                        if date_element:
                            content_parts = date_element.get_text().split('|')
                            if len(content_parts) > 1:
                                summary = content_parts[1].strip()
                        
                        categories = []
                        category_elements = article.find_all('a', rel='category tag')
                        for cat in category_elements:
                            categories.append(cat.get_text(strip=True))
                        
                        image_element = article.find('img')
                        image_url = image_element['data-src'] if image_element and 'data-src' in image_element.attrs else (
                            image_element['src'] if image_element and 'src' in image_element.attrs else None
                        )
                        
                        full_content = self.scrape_full_article(link)
                        
                        news_items.append({
                            'title': title,
                            'link': link,
                            'date': date_text,
                            'summary': summary,
                            'full_content': full_content,
                            'categories': categories,
                            'image_url': image_url,
                            'source': 'Investopaper'
                        })
                        
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"Error parsing article: {e}")
                        continue
                
                pagination = soup.find('ul', class_='default-wp-page')
                if pagination:
                    next_page = pagination.find('li', class_='next')
                    if next_page and next_page.find('a'):
                        pass
                
            except Exception as e:
                print(f"Error scraping {url_template}: {e}")
                continue
        
        filename = os.path.join(self.data_dir, f"{symbol.lower()}_news.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'symbol': symbol,
                'last_updated': datetime.now().isoformat(),
                'news': news_items
            }, f, indent=2, ensure_ascii=False)
        
        return len(news_items)