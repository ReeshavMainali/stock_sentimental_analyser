import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from urllib.parse import quote, urljoin
import time
import re

class NepseNewsScraper:
    def __init__(self):
        # Base URLs for different news sources
        self.investopaper_base_url = "https://www.investopaper.com"
        self.sharehub_base_url = "https://sharehubnepal.com"
        self.nepsealpha_base_url = "https://www.nepsealpha.com"
        self.sharesansar_base_url = "https://www.sharesansar.com"

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)

    def _scrape_full_article_investopaper(self, url):
        """
        Helper function to scrape the full content of an Investopaper article.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            article_content = soup.find('div', class_='entry-content')
            if not article_content:
                return "Full article content not found"
            
            # Remove unwanted elements (scripts, styles, ads, etc.)
            for element in article_content.find_all(['div', 'script', 'style', 'aside', 'pre', 'hr']):
                element.decompose()
                
            # Remove social media buttons
            for element in article_content.find_all(class_=['sfsiaftrpstwpr', 'sfsi_responsive_icons']):
                element.decompose()
                
            # Remove recommended links (specific to Investopaper structure)
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
            
        except requests.exceptions.RequestException as e:
            print(f"    [Investopaper] Error scraping full article from {url}: {e}")
            return "Error retrieving full article content"
        except Exception as e:
            print(f"    [Investopaper] General error scraping full article from {url}: {e}")
            return "Error retrieving full article content"

    def _scrape_investopaper_news(self, symbol):
        """
        Scrapes news articles for a given stock symbol from investopaper.com.
        """
        news_items = []
        url_template = f"{self.investopaper_base_url}/?s={{symbol}}"
        
        print(f"  [Investopaper] Fetching news for {symbol} from {url_template.format(symbol=symbol)}")

        try:
            url = url_template.format(symbol=quote(symbol))
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            article_container = soup.find('div', class_='article-container')
            if not article_container:
                print(f"  [Investopaper] No article container found for {symbol}.")
                return []
            
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
                    
                    full_content = self._scrape_full_article_investopaper(link)
                    
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
                    print(f"  [Investopaper] Error parsing article for {symbol}: {e}")
                    continue
            
            # Investopaper pagination logic (not fully implemented for multiple pages in this version)
            # pagination = soup.find('ul', class_='default-wp-page')
            # if pagination:
            #     next_page = pagination.find('li', class_='next')
            #     if next_page and next_page.find('a'):
            #         pass # Logic to go to next page
                
        except requests.exceptions.RequestException as e:
            print(f"  [Investopaper] Error scraping Investopaper for {symbol}: {e}")
        except Exception as e:
            print(f"  [Investopaper] General error scraping Investopaper for {symbol}: {e}")
            
        return news_items

    def _scrape_full_article_sharehubnepal(self, url):
        """
        Helper function to scrape the full content of a ShareHubNepal article.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"    [ShareHubNepal] Error fetching full article from {url}: {e}")
            return "Error retrieving full article content", None, None

        article_soup = BeautifulSoup(response.text, 'html.parser')
        article_content_div = article_soup.find('div', id='post-content')
        article_header = article_soup.find('header', class_='py-3')

        publish_date = None
        author = None # Will not be used in final output, but extracted for completeness
        full_content = "No readable content found"

        if article_header:
            # Extract author
            author_tag = article_header.find('a', href=re.compile(r'/author/'))
            if author_tag:
                author = author_tag.get_text(strip=True)

            # Extract publish date
            date_tag = article_header.find('span', class_=lambda x: x and 'text-grey-500' in x and 'font-normal' in x)
            if date_tag:
                publish_date = date_tag.get_text(strip=True)

        if article_content_div:
            paragraphs = article_content_div.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6'])
            content_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text:
                    content_parts.append(text)
            full_content = '\n\n'.join(content_parts) if content_parts else "No readable content found"

        return full_content, publish_date, author

    def _scrape_sharehubnepal_news(self, symbol):
        """
        Scrapes news articles for a given stock symbol from sharehubnepal.com.
        """
        news_list_url = f"{self.sharehub_base_url}/company/{symbol}/news"
        articles_data = []

        print(f"  [ShareHubNepal] Fetching news list for {symbol} from {news_list_url}")

        try:
            response = requests.get(news_list_url, headers=self.headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"  [ShareHubNepal] Error fetching news list for {symbol}: {e}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')

        news_container = soup.find('div', class_='grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-3 gap-4 md:gap-8 mt-2')

        if not news_container:
            print(f"  [ShareHubNepal] No news container found for {symbol}.")
            return []

        news_items_html = news_container.find_all('div', class_='flex p-3 rounded-md border hover:cursor-pointer items-center gap-4')

        if not news_items_html:
            print(f"  [ShareHubNepal] No news items found for {symbol}.")
            return []

        for item_html in news_items_html:
            article_relative_url = None
            link_tag = item_html.find('a')
            if link_tag and 'href' in link_tag.attrs:
                article_relative_url = link_tag['href']
            else:
                title_span = item_html.find('span', class_=lambda x: x and 'font-semibold' in x)
                if title_span:
                    parent_link = title_span.find_parent('a')
                    if parent_link and 'href' in parent_link.attrs:
                        article_relative_url = parent_link['href']

            if not article_relative_url:
                print("  [ShareHubNepal] Could not find a valid link within the news item. Skipping.")
                continue

            article_url = urljoin(self.sharehub_base_url, article_relative_url)
            print(f"    [ShareHubNepal] Scraping article from: {article_url}")

            full_content, publish_date, _ = self._scrape_full_article_sharehubnepal(article_url) # Author not needed in final format

            title_span_in_list = item_html.find('span', class_=lambda x: x and 'font-semibold' in x)
            title = title_span_in_list.get_text(strip=True) if title_span_in_list else ""
            
            # Image URL from listing
            image_element = item_html.find('img')
            image_url = image_element['src'] if image_element and 'src' in image_element.attrs else None

            articles_data.append({
                'title': title,
                'link': article_url,
                'date': publish_date,
                'summary': None, # ShareHubNepal doesn't provide summary in listing
                'full_content': full_content,
                'categories': [], # ShareHubNepal doesn't provide categories in listing
                'image_url': image_url,
                'source': 'ShareHubNepal'
            })
            time.sleep(1) 

        return articles_data

    def _scrape_full_article_nepsealpha(self, url):
        """
        Helper function to scrape the full content of a NepseAlpha article.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract article date from post details
            article_date = None
            date_element = soup.find('li', class_='detail date')
            if date_element:
                article_date = date_element.get_text(strip=True)
            
            # Extract main content
            content_div = soup.find('div', {'id': 'postDescriptions'})
            if not content_div:
                return "Content not found", article_date
            
            # Clean and get text
            paragraphs = []
            for p in content_div.find_all('p'):
                text = p.get_text(strip=True)
                if text and not text.startswith(('©', 'License:', 'Author:')):
                    paragraphs.append(text)
            
            content = '\n\n'.join(paragraphs) if paragraphs else "No readable content found"
            return content, article_date
            
        except requests.exceptions.RequestException as e:
            print(f"    [NepseAlpha] Error scraping full article from {url}: {e}")
            return "Error retrieving full article content", None
        except Exception as e:
            print(f"    [NepseAlpha] General error scraping full article from {url}: {e}")
            return "Error retrieving full article content", None

    def _scrape_nepsealpha_news(self, symbol):
        """
        Scrapes news articles for a given stock symbol from nepsealpha.com.
        """
        news_items = []
        search_url = f"{self.nepsealpha_base_url}/search?q={symbol}"
        
        print(f"  [NepseAlpha] Fetching news list for {symbol} from {search_url}")

        try:
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_table = soup.find('table', {'id': 'news_tables'})
            if not news_table:
                print(f"  [NepseAlpha] No news table found for {symbol}")
                return []
            
            rows = news_table.find('tbody').find_all('tr')
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                        
                    date = cells[0].get_text(strip=True)
                    title_link = cells[1].find('a')
                    if not title_link:
                        continue
                        
                    title = title_link.get_text(strip=True)
                    article_url = title_link['href']
                    
                    if not article_url.startswith('http'):
                        article_url = urljoin(self.nepsealpha_base_url, article_url)
                    
                    print(f"    [NepseAlpha] Scraping article from: {article_url}")
                    full_content, article_date = self._scrape_full_article_nepsealpha(article_url)
                    
                    date = article_date if article_date else date
                    
                    news_items.append({
                        'title': title,
                        'link': article_url,
                        'date': date,
                        'summary': None, # NepseAlpha doesn't provide summary in listing
                        'full_content': full_content,
                        'categories': [], # NepseAlpha doesn't provide categories
                        'image_url': None, # NepseAlpha doesn't provide image URL in listing
                        'source': 'NepseAlpha'
                    })
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"  [NepseAlpha] Error processing news row for {symbol}: {e}")
                    continue
                    
        except requests.exceptions.RequestException as e:
            print(f"  [NepseAlpha] Error searching news for {symbol}: {e}")
        except Exception as e:
            print(f"  [NepseAlpha] General error scraping NepseAlpha for {symbol}: {e}")
            
        return news_items

    def _scrape_full_article_sharesansar(self, url):
        """
        Helper function to scrape the full content of a Sharesansar article.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content_div = soup.find('div', {'id': 'newsdetail-content'})
            if not content_div:
                return "Content not found"
            
            # Remove unwanted elements
            for element in content_div.find_all(['div', 'script', 'style', 'aside', 'figure', 'img']):
                element.decompose()
                
            paragraphs = []
            for p in content_div.find_all('p'):
                text = p.get_text(strip=True)
                if text and not text.startswith(('©', 'License:', 'Author:')):
                    paragraphs.append(text)
            
            return '\n\n'.join(paragraphs) if paragraphs else "No readable content found"
            
        except requests.exceptions.RequestException as e:
            print(f"    [Sharesansar] Error scraping full article from {url}: {e}")
            return "Error retrieving full article content"
        except Exception as e:
            print(f"    [Sharesansar] General error scraping full article from {url}: {e}")
            return "Error retrieving full article content"

    def _scrape_sharesansar_news(self, symbol):
        """
        Scrapes news articles for a given stock symbol from sharesansar.com.
        """
        news_items = []
        company_url = f"{self.sharesansar_base_url}/company/{symbol}"
        
        print(f"  [Sharesansar] Fetching news list for {symbol} from {company_url}")

        try:
            response = requests.get(company_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_table = soup.find('table', {'id': 'myTableCNews'})
            if not news_table:
                print(f"  [Sharesansar] No news table found for {symbol}")
                return []
            
            rows = news_table.find('tbody').find_all('tr')
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                        
                    date = cells[0].get_text(strip=True)
                    title_link = cells[1].find('a')
                    if not title_link:
                        continue
                        
                    title = title_link.get_text(strip=True)
                    relative_url = title_link['href']
                    full_url = urljoin(self.sharesansar_base_url, relative_url)
                    
                    print(f"    [Sharesansar] Scraping article from: {full_url}")
                    full_content = self._scrape_full_article_sharesansar(full_url)
                    
                    news_items.append({
                        'title': title,
                        'link': full_url,
                        'date': date,
                        'summary': None, # Sharesansar doesn't provide summary in listing
                        'full_content': full_content,
                        'categories': [], # Sharesansar doesn't provide categories
                        'image_url': None, # Sharesansar doesn't provide image URL in listing
                        'source': 'Sharesansar'
                    })
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"  [Sharesansar] Error processing news row for {symbol}: {e}")
                    continue
                    
        except requests.exceptions.RequestException as e:
            print(f"  [Sharesansar] Error scraping company page for {symbol}: {e}")
        except Exception as e:
            print(f"  [Sharesansar] General error scraping Sharesansar for {symbol}: {e}")
            
        return news_items

    def scrape_news(self, symbol):
        """
        Main method to scrape news for a given symbol from all integrated sources.
        Combines and standardizes the output.

        Args:
            symbol (str): The stock symbol (e.g., 'NABIL', 'NTC').

        Returns:
            list: A list of dictionaries, where each dictionary represents a news item
                  in the standardized format.
        """
        all_news_for_symbol = []
        
        print(f"\n--- Starting unified news scraping for symbol: {symbol} ---")

        # Scrape from Investopaper
        investopaper_news = self._scrape_investopaper_news(symbol)
        if investopaper_news:
            all_news_for_symbol.extend(investopaper_news)
            print(f"  [Investopaper] Scraped {len(investopaper_news)} news items for {symbol}.")
        else:
            print(f"  [Investopaper] No news found for {symbol}.")
        time.sleep(2) # Pause between sources

        # Scrape from ShareHubNepal
        sharehub_news = self._scrape_sharehubnepal_news(symbol)
        if sharehub_news:
            all_news_for_symbol.extend(sharehub_news)
            print(f"  [ShareHubNepal] Scraped {len(sharehub_news)} news items for {symbol}.")
        else:
            print(f"  [ShareHubNepal] No news found for {symbol}.")
        time.sleep(2) # Pause between sources

        # Scrape from NepseAlpha
        nepsealpha_news = self._scrape_nepsealpha_news(symbol)
        if nepsealpha_news:
            all_news_for_symbol.extend(nepsealpha_news)
            print(f"  [NepseAlpha] Scraped {len(nepsealpha_news)} news items for {symbol}.")
        else:
            print(f"  [NepseAlpha] No news found for {symbol}.")
        time.sleep(2) # Pause between sources

        # Scrape from Sharesansar
        sharesansar_news = self._scrape_sharesansar_news(symbol)
        if sharesansar_news:
            all_news_for_symbol.extend(sharesansar_news)
            print(f"  [Sharesansar] Scraped {len(sharesansar_news)} news items for {symbol}.")
        else:
            print(f"  [Sharesansar] No news found for {symbol}.")
        time.sleep(2) # Pause between sources
        
        print(f"--- Finished unified news scraping for {symbol}. Total news items: {len(all_news_for_symbol)} ---")
        
        # Save the combined news for this symbol to a JSON file
        filename = os.path.join(self.data_dir, f"{symbol.lower()}_news.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'symbol': symbol,
                'last_updated': datetime.now().isoformat(),
                'news': all_news_for_symbol
            }, f, indent=2, ensure_ascii=False)
        print(f"Unified data for {symbol} saved to {filename}")

        return all_news_for_symbol

# Example usage:
# if __name__ == "__main__":
#     scraper = NepseNewsScraper()
    
    # Define the list of company symbols you want to scrape
    # Use actual symbols recognized by the websites (e.g., 'NABIL', 'NTC', 'GBIME', 'HBL')
    # company_symbols_to_scrape = ['NABIL', 'NTC'] # Add more symbols as needed

    # for symbol in company_symbols_to_scrape:
    #     scraped_news_items = scraper.scrape_news(symbol)
    #     print(f"\nSummary for {symbol}: {len(scraped_news_items)} articles scraped and saved.")
        # You can optionally print some details here
        # for item in scraped_news_items[:3]: # Print first 3 articles
        #     print(f"  Title: {item['title']}")
        #     print(f"  Source: {item['source']}")
        #     print(f"  Date: {item['date']}")
        #     print(f"  Link: {item['link']}")
        #     print("-" * 20)
