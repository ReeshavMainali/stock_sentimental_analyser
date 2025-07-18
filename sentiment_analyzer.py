import os
import json
from ollama import Client
from typing import List, Dict

class SentimentAnalyzer:
    def __init__(self):
        self.client = Client(host='http://localhost:11434')
        self.model_name = "gemma3:4b"
        self.data_dir = "data"
    
    def analyze_sentiment(self, text: str) -> Dict:
        prompt = f"""
        Analyze the sentiment of the following financial news text related to a NEPSE stock.
        Determine the sentiment distribution (Positive, Negative) and provide specific remarks.

        Return ONLY in this exact format:
        | Sentiment       | Percentage | Remarks                                    |
        |-----------------|------------|--------------------------------------------|
        | Positive        | XX%        | [Specific positive aspects from the text]  |
        | Negative        | YY%        | [Specific negative aspects from the text]  |

        Rules:
        1. The percentages must add up to 100%
        2. Remarks should be concise bullet points from the text
        3. Focus on financial indicators like profit, revenue, expenses, growth, etc.
        4. If text is neutral, use 50%-50% distribution

        Text to analyze:
        {text}
        """
        
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={'temperature': 0.2, 'num_ctx': 4096}
            )
            return self._parse_response(response['response'])
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return {
                'sentiment_table': "| Sentiment       | Percentage | Remarks               |\n" +
                                  "|-----------------|------------|-----------------------|\n" +
                                  "| Positive        | 50%        | Neutral content       |\n" +
                                  "| Negative        | 50%        | Neutral content       |"
            }
    
    def _parse_response(self, response_text: str) -> Dict:
        # Extract the table part from the response
        table_start = response_text.find("| Sentiment")
        table_end = response_text.find("\n\n", table_start)
        table = response_text[table_start:table_end].strip() if table_start != -1 else response_text
        
        return {
            'sentiment_table': table
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
            analysis = self.analyze_sentiment(news_item['title'] + "\n" + news_item['full_content'])
            analyzed_news.append({
                'title': news_item['title'],
                'link': news_item['link'],
                'date': news_item['date'],
                'sentiment_analysis': analysis['sentiment_table'],
                'source': news_item['source']
            })
        
        return analyzed_news
    
    def generate_report(self, symbol: str, analyzed_news: List[Dict]) -> str:
        if not analyzed_news:
            return f"No news analyzed for {symbol}"
        
        # Calculate overall sentiment percentages
        positive_sum = 0
        negative_sum = 0
        count = 0
        
        for item in analyzed_news:
            lines = item['sentiment_analysis'].split('\n')
            if len(lines) >= 3:
                positive_line = lines[2].split('|')
                if len(positive_line) > 3:
                    positive_pct = positive_line[2].strip().replace('%','')
                    try:
                        positive_sum += float(positive_pct)
                        count += 1
                    except ValueError:
                        pass
                
                if len(lines) >= 4:
                    negative_line = lines[3].split('|')
                    if len(negative_line) > 3:
                        negative_pct = negative_line[2].strip().replace('%','')
                        try:
                            negative_sum += float(negative_pct)
                        except ValueError:
                            pass
        
        avg_positive = round(positive_sum / count) if count > 0 else 50
        avg_negative = 100 - avg_positive
        
        # Generate report
        report_lines = [
            f"Sentiment Analysis Report for {symbol.upper()}",
            "=" * 60,
            f"Total News Analyzed: {len(analyzed_news)}",
            "\nOverall Sentiment Distribution:",
            "| Sentiment       | Percentage |",
            "|-----------------|------------|",
            f"| Positive        | {avg_positive}%        |",
            f"| Negative        | {avg_negative}%        |",
            "\nDetailed Analysis:",
            "=" * 60
        ]
        
        for item in analyzed_news:
            report_lines.extend([
                f"\nTitle: {item['title']}",
                f"Date: {item['date']}",
                f"Source: {item['source']}",
                f"Link: {item['link']}",
                "\nSentiment Analysis:",
                item['sentiment_analysis'],
                "-" * 60
            ])
        
        return "\n".join(report_lines)