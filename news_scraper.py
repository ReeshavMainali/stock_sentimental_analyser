import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from urllib.parse import quote, urljoin
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

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

    def _scrape_full_article_sharehubnepal(self, driver, url):
        """
        Helper function to scrape the full content of a ShareHubNepal article using Selenium.
        
        Args:
            driver (selenium.webdriver.remote.webdriver.WebDriver): The Selenium WebDriver instance.
            url (str): The URL of the news article.

        Returns:
            tuple: A tuple containing (str: full article content, str: publish date).
                Returns ("Error retrieving full article content", None) on error.
        """
        try:
            print(f"    [ShareHubNepal] Navigating to article: {url}")
            driver.get(url)
            
            # Wait for the main content div to be present
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "post-content"))
            )
            
            article_soup = BeautifulSoup(driver.page_source, 'html.parser')
            article_content_div = article_soup.find('div', id='post-content')
            article_header = article_soup.find('header', class_='py-3')

            publish_date = None
            full_content = "No readable content found"

            if article_header:
                # Extract publish date
                # The date is in a span with classes like 'text-grey-500' and 'font-normal'
                date_tag = article_header.find('span', class_=lambda x: x and 'text-grey-500' in x and 'font-normal' in x)
                if date_tag:
                    publish_date = date_tag.get_text(strip=True)

            if article_content_div:
                # Collect text from various heading and paragraph tags
                paragraphs = article_content_div.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6'])
                content_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text:
                        content_parts.append(text)
                full_content = '\n\n'.join(content_parts) if content_parts else "No readable content found"

            return full_content, publish_date
                
        except TimeoutException:
            print(f"    [ShareHubNepal] Timeout waiting for article content on {url}")
            return "Timeout retrieving full article content", None
        except WebDriverException as e:
            print(f"    [ShareHubNepal] WebDriver error scraping full article from {url}: {e}")
            return "Error retrieving full article content", None
        except Exception as e:
            print(f"    [ShareHubNepal] General error scraping full article from {url}: {e}")
            return "Error retrieving full article content", None

    def _scrape_sharehubnepal_news(self, driver, symbol):
        """
        Scrapes news articles for a given stock symbol from sharehubnepal.com.
        This function uses Selenium to interact with the dynamic content.

        Args:
            driver (selenium.webdriver.remote.webdriver.WebDriver): The Selenium WebDriver instance.
            symbol (str): The company symbol (e.g., 'ACLBSL').

        Returns:
            list: A list of dictionaries, where each dictionary contains
                'title', 'link', 'date', 'summary', 'full_content',
                'categories', 'image_url', and 'source'.
        """
        news_list_url = f"{self.sharehub_base_url}/company/{symbol}/news"
        articles_data = []

        print(f"  [ShareHubNepal] Fetching news list for {symbol} from {news_list_url}")

        try:
            driver.get(news_list_url)
            
            # ShareHubNepal news seems to be directly loaded on the URL, no tab click needed.
            # Wait for the news container to be visible
            news_container_class = 'grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-3 gap-4 md:gap-8 mt-2'
            try:
                WebDriverWait(driver, 20).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, news_container_class.split(' ')[0])) # Use first class for simplicity
                )
                time.sleep(2) # Give a little extra time for all cards to render
            except TimeoutException:
                print(f"  [ShareHubNepal] Timeout waiting for news container to be visible.")
                return []
            except Exception as e:
                print(f"  [ShareHubNepal] Error waiting for news container: {e}")
                return []

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            news_container = soup.find('div', class_=news_container_class)

            if not news_container:
                print(f"  [ShareHubNepal] No news container found for {symbol}.")
                return []

            # News items are in divs with specific classes
            news_items_html = news_container.find_all('div', class_='flex p-3 rounded-md border hover:cursor-pointer items-center gap-4')

            if not news_items_html:
                print(f"  [ShareHubNepal] No news items found for {symbol}.")
                return []

            for item_html in news_items_html:
                try:
                    article_relative_url = None
                    link_tag = item_html.find('a') # The main link wraps the whole card
                    if link_tag and 'href' in link_tag.attrs:
                        article_relative_url = link_tag['href']
                    else:
                        # Fallback if the direct link is not the primary 'a' tag
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

                    full_content, publish_date = self._scrape_full_article_sharehubnepal(driver, article_url)
                    
                    # Extract title from the listing card
                    title_span_in_list = item_html.find('span', class_=lambda x: x and 'font-semibold' in x)
                    title = title_span_in_list.get_text(strip=True) if title_span_in_list else ""
                    
                    # Extract image URL from listing
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
                    time.sleep(1) # Be polite to the server

                except Exception as e:
                    print(f"  [ShareHubNepal] Error processing news item for {symbol}: {e}")
                    continue
                    
        except WebDriverException as e:
            print(f"  [ShareHubNepal] WebDriver error navigating to news list for {symbol}: {e}")
        except Exception as e:
            print(f"  [ShareHubNepal] General error scraping ShareHubNepal for {symbol}: {e}")
                
        return articles_data
        


    def _scrape_full_article_nepsealpha(self, driver, url):
        """
        Helper function to scrape the full content of a NepseAlpha article using Selenium.
        
        Args:
            driver (selenium.webdriver.remote.webdriver.WebDriver): The Selenium WebDriver instance.
            url (str): The URL of the news article.

        Returns:
            tuple: A tuple containing (str: full article content, str: article date).
                Returns ("Error retrieving full article content", None) on error.
        """
        try:
            print(f"    [NepseAlpha] Navigating to article: {url}")
            driver.get(url)
            
            # Wait for the main content div to be present
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "postDescriptions"))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract article date from post details
            article_date = None
            date_element = soup.find('li', class_='detail date')
            if date_element:
                article_date = date_element.get_text(strip=True)
            
            # Extract main content
            content_div = soup.find('div', {'id': 'postDescriptions'})
            if not content_div:
                print(f"    [NepseAlpha] Content div 'postDescriptions' not found for {url}")
                return "Content not found", article_date
            
            # Clean and get text (remove unwanted elements within the content div)
            # Note: The user's original NepseAlpha snippet did not have explicit element removal
            # but it's good practice. I'll stick to the user's provided filtering for paragraphs.
            
            paragraphs = []
            for p in content_div.find_all('p'):
                text = p.get_text(strip=True)
                if text and not text.startswith(('©', 'License:', 'Author:')):
                    paragraphs.append(text)
            
            content = '\n\n'.join(paragraphs) if paragraphs else "No readable content found"
            return content, article_date
                
        except TimeoutException:
            print(f"    [NepseAlpha] Timeout waiting for article content on {url}")
            return "Timeout retrieving full article content", None
        except WebDriverException as e:
            print(f"    [NepseAlpha] WebDriver error scraping full article from {url}: {e}")
            return "Error retrieving full article content", None
        except Exception as e:
            print(f"    [NepseAlpha] General error scraping full article from {url}: {e}")
            return "Error retrieving full article content", None

    def _scrape_nepsealpha_news(self, driver, symbol):
        """
        Scrapes news articles for a given stock symbol from nepsealpha.com.
        This function uses Selenium to interact with the dynamic content.

        Args:
            driver (selenium.webdriver.remote.webdriver.WebDriver): The Selenium WebDriver instance.
            nepsealpha_base_url (str): The base URL for NepseAlpha (e.g., "https://www.nepsealpha.com").
            symbol (str): The company symbol (e.g., 'NABIL').

        Returns:
            list: A list of dictionaries, where each dictionary contains
                'title', 'link', 'date', 'summary', 'full_content',
                'categories', 'image_url', and 'source'.
        """
        news_items = []
        search_url = f"{self.nepsealpha_base_url}/search?q={symbol}"
        
        print(f"  [NepseAlpha] Fetching news list for {symbol} from {search_url}")

        try:
            driver.get(search_url)

            # --- Click the 'News' tab ---
            print("  [NepseAlpha] Clicking the 'News' tab...")
            # Find the news tab by its href attribute or text
            news_tab_xpath = "//ul[@id='details-tabs']//a[@href='#news' and contains(., 'News')]"
            try:
                # Wait for the news tab to be clickable
                news_tab = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, news_tab_xpath))
                )
                news_tab.click()
                # Give some time for the content to load after clicking the tab
                time.sleep(3) # A short pause to allow JS to render the table
            except TimeoutException:
                print(f"  [NepseAlpha] Timeout waiting for News tab to be clickable.")
                return []
            except Exception as e:
                print(f"  [NepseAlpha] Could not click the News tab or it did not load: {e}")
                return []

            # --- Extract news headlines and links from the table ---
            print("  [NepseAlpha] Extracting news headlines and links from the table...")
            news_table_id = "news_tables"
            try:
                # Wait for the news table to be visible
                WebDriverWait(driver, 20).until(
                    EC.visibility_of_element_located((By.ID, news_table_id))
                )
                # Get the page source after dynamic content has loaded
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                news_table = soup.find('table', id=news_table_id)
                if not news_table:
                    print("  [NepseAlpha] News table 'news_tables' not found after clicking tab.")
                    return []

                rows = news_table.find('tbody').find_all('tr')
                if not rows:
                    print("  [NepseAlpha] No news rows found in the table.")
                    return []

                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 2:
                            continue # Skip malformed rows
                            
                        date_from_list = cells[0].get_text(strip=True) # Date from the listing table
                        title_link = cells[1].find('a')
                        if not title_link:
                            continue
                            
                        title = title_link.get_text(strip=True)
                        article_url = title_link['href']
                        
                        if not article_url.startswith('http'):
                            article_url = urljoin(self.nepsealpha_base_url, article_url)
                        
                        # Scrape the full article content and its specific date
                        full_content, article_date_from_page = self._scrape_full_article_nepsealpha(driver, article_url)
                        
                        # Use the date from the article page if available, otherwise use the list date
                        final_date = article_date_from_page if article_date_from_page else date_from_list
                        
                        news_items.append({
                            'title': title,
                            'link': article_url,
                            'date': final_date,
                            'summary': None, # NepseAlpha doesn't provide summary in listing
                            'full_content': full_content,
                            'categories': [], # NepseAlpha doesn't provide categories
                            'image_url': None, # NepseAlpha doesn't provide image URL in listing
                            'source': 'NepseAlpha'
                        })
                        
                        time.sleep(1) # Be polite to the server
                        
                    except Exception as e:
                        print(f"  [NepseAlpha] Error processing news row for {symbol}: {e}")
                        continue
                        
            except TimeoutException:
                print(f"  [NepseAlpha] Timeout waiting for news table '{news_table_id}' to be visible.")
        except WebDriverException as e:
            print(f"  [NepseAlpha] WebDriver error navigating to search page for {symbol}: {e}")
        except Exception as e:
            print(f"  [NepseAlpha] General error scraping NepseAlpha for {symbol}: {e}")
                
        return news_items

    def _scrape_full_article_sharesansar(self, driver, url):
        """
        Helper function to scrape the full content of a Sharesansar article using Selenium.
        
        Args:
            driver (selenium.webdriver.remote.webdriver.WebDriver): The Selenium WebDriver instance.
            url (str): The URL of the news article.

        Returns:
            str: The extracted full article content, or an error message.
        """
        try:
            print(f"    [Sharesansar] Navigating to article: {url}")
            driver.get(url)
            
            # Wait for the main content div to be present
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "newsdetail-content"))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            content_div = soup.find('div', {'id': 'newsdetail-content'})
            if not content_div:
                print(f"    [Sharesansar] Content div 'newsdetail-content' not found for {url}")
                return "Content not found"
            
            # Remove unwanted elements as specified
            for element in content_div.find_all(['div', 'script', 'style', 'aside', 'figure', 'img']):
                element.decompose()
                
            paragraphs = []
            # Find all paragraph tags within the cleaned content div
            for p in content_div.find_all('p'):
                text = p.get_text(strip=True)
                # Filter out specific unwanted texts
                if text and not text.startswith(('©', 'License:', 'Author:')):
                    paragraphs.append(text)
            
            return '\n\n'.join(paragraphs) if paragraphs else "No readable content found"
            
        except TimeoutException:
            print(f"    [Sharesansar] Timeout waiting for article content on {url}")
            return "Timeout retrieving full article content"
        except WebDriverException as e:
            print(f"    [Sharesansar] WebDriver error scraping full article from {url}: {e}")
            return "Error retrieving full article content"
        except Exception as e:
            print(f"    [Sharesansar] General error scraping full article from {url}: {e}")
            return "Error retrieving full article content"

    def _scrape_sharesansar_news(self, driver, symbol):
        """
        Scrapes news articles for a given stock symbol from sharesansar.com.
        This function uses Selenium to interact with the dynamic content.

        Args:
            driver (selenium.webdriver.remote.webdriver.WebDriver): The Selenium WebDriver instance.
            sharesansar_base_url (str): The base URL for Sharesansar (e.g., "https://www.sharesansar.com").
            symbol (str): The company symbol (e.g., 'NABIL').

        Returns:
            list: A list of dictionaries, where each dictionary contains
                'title', 'link', 'date', 'summary', 'full_content',
                'categories', 'image_url', and 'source'.
        """
        news_items = []
        company_url = f"{self.sharesansar_base_url}/company/{symbol}"
        
        print(f"  [Sharesansar] Fetching news list for {symbol} from {company_url}")

        try:
            driver.get(company_url)

            # --- Click the 'News' tab ---
            print("  [Sharesansar] Clicking the 'News' tab...")
            news_tab_id = "btn_cnews"
            try:
                # Wait for the news tab to be clickable
                news_tab = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.ID, news_tab_id))
                )
                news_tab.click()
                # Give some time for the content to load after clicking the tab
                time.sleep(3) # A short pause to allow JS to render the table
            except TimeoutException:
                print(f"  [Sharesansar] Timeout waiting for News tab '{news_tab_id}' to be clickable.")
                return []
            except Exception as e:
                print(f"  [Sharesansar] Could not click the News tab or it did not load: {e}")
                return []

            # --- Extract news headlines and links from the table ---
            print("  [Sharesansar] Extracting news headlines and links from the table...")
            news_table_id = "myTableCNews"
            try:
                # Wait for the news table to be visible
                WebDriverWait(driver, 20).until(
                    EC.visibility_of_element_located((By.ID, news_table_id))
                )
                # Get the page source after dynamic content has loaded
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                news_table = soup.find('table', id=news_table_id)
                if not news_table:
                    print("  [Sharesansar] News table 'myTableCNews' not found after clicking tab.")
                    return []

                rows = news_table.find('tbody').find_all('tr')
                if not rows:
                    print("  [Sharesansar] No news rows found in the table.")
                    return []

                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 2:
                            continue # Skip malformed rows
                            
                        date = cells[0].get_text(strip=True)
                        title_link = cells[1].find('a')
                        if not title_link:
                            continue
                            
                        title = title_link.get_text(strip=True)
                        relative_url = title_link['href']
                        full_url = urljoin(self.sharesansar_base_url, relative_url)
                        
                        # Scrape the full article content
                        full_content = self._scrape_full_article_sharesansar(driver, full_url)
                        
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
                        
                        time.sleep(1) # Be polite to the server
                        
                    except Exception as e:
                        print(f"  [Sharesansar] Error processing news row for {symbol}: {e}")
                        continue
                        
            except TimeoutException:
                print(f"  [Sharesansar] Timeout waiting for news table '{news_table_id}' to be visible.")
        except WebDriverException as e:
            print(f"  [Sharesansar] WebDriver error navigating to company page for {symbol}: {e}")
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

        # --- Selenium-based scraping ---
        driver = None
        try:
            # It's good practice to use headless mode for scraping
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            driver = webdriver.Chrome(options=options)

            # Scrape from ShareHubNepal
            sharehub_news = self._scrape_sharehubnepal_news(driver, symbol)
            if sharehub_news:
                all_news_for_symbol.extend(sharehub_news)
                print(f"  [ShareHubNepal] Scraped {len(sharehub_news)} news items for {symbol}.")
            else:
                print(f"  [ShareHubNepal] No news found for {symbol}.")
            time.sleep(2) # Pause between sources

            # Scrape from NepseAlpha
            nepsealpha_news = self._scrape_nepsealpha_news(driver, symbol)
            if nepsealpha_news:
                all_news_for_symbol.extend(nepsealpha_news)
                print(f"  [NepseAlpha] Scraped {len(nepsealpha_news)} news items for {symbol}.")
            else:
                print(f"  [NepseAlpha] No news found for {symbol}.")
            time.sleep(2)

            # Scrape from Sharesansar
            sharesansar_news = self._scrape_sharesansar_news(driver, symbol)
            if sharesansar_news:
                all_news_for_symbol.extend(sharesansar_news)
                print(f"  [Sharesansar] Scraped {len(sharesansar_news)} news items for {symbol}.")
            else:
                print(f"  [Sharesansar] No news found for {symbol}.")
            time.sleep(2)

        except WebDriverException as e:
            print(f"  [Selenium] WebDriver error during scraping for {symbol}: {e}")
            print("  [Selenium] Please ensure you have chromedriver installed and in your PATH.")
        except Exception as e:
            print(f"  [Selenium] A general error occurred during selenium scraping for {symbol}: {e}")
        finally:
            if driver:
                driver.quit()
        
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
