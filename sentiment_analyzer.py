import json
import os
from ollama import Client
from typing import List, Dict

class SentimentAnalyzer:
    def __init__(self):
        self.client = Client(host='http://localhost:11434')
        self.model_name = "gemma3:4b"
        self.data_dir = "data"
    
    def analyze_sentiment(self, text: str) -> Dict:
        prompt = f"""
            ### Persona ###
            You are an expert financial analyst specializing in the Nepal Stock Exchange (NEPSE). You are objective, data-driven, and understand the nuances of financial reporting, including company performance, market trends, and regulatory announcements from bodies like SEBON.

            ### Primary Task ###
            Analyze the sentiment of the following financial news text concerning a NEPSE-listed company or the market in general. Your analysis should determine if the sentiment is Positive, Negative, or Neutral from an investor's perspective.

            ### Analysis Guidelines & Rules ###
            1.  **Identify Key Information:** First, identify the core financial facts in the text. Look for keywords related to earnings, revenue, profit, loss, dividends, expansion, debt, regulatory actions, and market performance.
            2.  **Weigh Conflicting Information:** News can be mixed. For example, "Profit fell but beat analyst expectations." Acknowledge this nuance. The final sentiment should reflect the dominant theme or the most impactful piece of information for an investor.
            3.  **Consider the Source and Context:** A company press release about "record growth" is different from a regulatory body announcing an investigation. The former is positive, the latter is likely negative.
            4.  **Define Neutrality:** A neutral text is purely factual and devoid of sentiment-laden language. Examples include announcements of an Annual General Meeting (AGM) date, a change in a minor executive role, or a simple market data report without commentary.
            5.  **Score with Justification:** Assign a sentiment score based on the scale below. Your justification is crucial as it explains your reasoning.

            ### Scoring Scale ###
            * **+8 to +10 (Strongly Positive):** Major positive news. (e.g., record-breaking profits, large dividend declaration, successful major expansion).
            * **+4 to +7 (Moderately Positive):** Clearly positive news. (e.g., solid profit growth, beating expectations, new product launch).
            * **+1 to +3 (Slightly Positive):** Minor positive news or a cautiously optimistic outlook.
            * **0 (Neutral):** Factual, non-speculative, no clear impact on investor sentiment.
            * **-1 to -3 (Slightly Negative):** Minor negative news. (e.g., slight dip in profit, cautionary outlook).
            * **-4 to -7 (Moderately Negative):** Clearly negative news. (e.g., significant profit decline, revenue miss, credit downgrade).
            * **-8 to -10 (Strongly Negative):** Major negative news. (e.g., reporting a huge loss, regulatory investigation, bankruptcy fears, delisting).

            ### Required Output Format ###
            Return ONLY the following structure. Do not add any other text or explanation outside this format.
            Give the output in a *Markdown table* format with these columns:

            | Sentiment       | Percentage | Remarks (2-3 lines explaining why) |

            First calculate positive % and negative % based on financial performance, and then explain clearly in remarks.


            ### Text to Analyze ###
            {text}
            """
        
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={'temperature': 0.2}  # Lower temperature for more deterministic results
            )
            
            result = self._parse_response(response['response'])
            return result
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return {
                'sentiment': 'Neutral',
                'score': 0
            }
    
    def _parse_response(self, response_text: str) -> Dict:
        lines = response_text.strip().split('\n')
        sentiment = "Neutral"
        score = 0
        
        for line in lines:
            if line.startswith("Sentiment:"):
                sentiment = line.split(":")[1].strip()
            elif line.startswith("Sentiment Score:"):
                try:
                    score = int(line.split(":")[1].strip())
                except ValueError:
                    score = 0
        
        return {
            'sentiment': sentiment,
            'score': score
        }
    
    def analyze_news_for_symbol(self, symbol: str) -> List[Dict]:
        filename = os.path.join(self.data_dir, f"{symbol.lower()}_news.json")
        
        if not os.path.exists(filename):
            print(f"No news data found for {symbol}")
            return []
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        analyzed_news = []
        for news_item in data['news']:
            analysis = self.analyze_sentiment(news_item['title'])
            analyzed_news.append({
                'title': news_item['title'],
                'link': news_item['link'],
                'source': news_item['source'],
                'sentiment': analysis['sentiment'],
                'score': analysis['score']
            })
        
        return analyzed_news
    
    def generate_report(self, symbol: str, analyzed_news: List[Dict]) -> str:
        if not analyzed_news:
            return f"No news analyzed for {symbol}"
        
        positive = sum(1 for item in analyzed_news if item['sentiment'] == 'Positive')
        negative = sum(1 for item in analyzed_news if item['sentiment'] == 'Negative')
        neutral = sum(1 for item in analyzed_news if item['sentiment'] == 'Neutral')
        
        avg_score = sum(item['score'] for item in analyzed_news) / len(analyzed_news)
        
        report_lines = [
            f"Sentiment Analysis Report for {symbol.upper()}",
            "=" * 40,
            f"Total News Analyzed: {len(analyzed_news)}",
            f"Positive Sentiment: {positive}",
            f"Negative Sentiment: {negative}",
            f"Neutral Sentiment: {neutral}",
            f"Average Sentiment Score: {avg_score:.2f}",
            "\nDetailed Analysis:",
            "-" * 40
        ]
        
        for item in analyzed_news:
            report_lines.append(
                f"Title: {item['title']}\n"
                f"Source: {item['source']}\n"
                f"Sentiment: {item['sentiment']}\n"
                f"Score: {item['score']}\n"
                f"Link: {item['link']}\n"
                "-" * 20
            )
        
        return "\n".join(report_lines)