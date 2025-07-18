import argparse
from news_scraper import NepseNewsScraper
from sentiment_analyzer import SentimentAnalyzer
import json

def main():
    parser = argparse.ArgumentParser(description="NEPSE Stock News Sentiment Analysis")
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape news for a NEPSE stock symbol')
    scrape_parser.add_argument('symbol', type=str, help='NEPSE stock symbol to scrape news for')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze sentiment of scraped news')
    analyze_parser.add_argument('symbol', type=str, help='NEPSE stock symbol to analyze')
    analyze_parser.add_argument('--report', action='store_true', help='Generate a detailed report')
    
    args = parser.parse_args()
    
    if args.command == 'scrape':
        scraper = NepseNewsScraper()
        count = scraper.scrape_news(args.symbol)
        print(f"Scraped {count} news items for {args.symbol.upper()}")
    
    elif args.command == 'analyze':
        analyzer = SentimentAnalyzer()
        analyzed_news = analyzer.analyze_news_for_symbol(args.symbol)
        
        if args.report:
            report = analyzer.generate_report(args.symbol, analyzed_news)
            print(report)
            
            # Save report to file
            with open(f"{args.symbol.lower()}_sentiment_report.txt", 'w', encoding='utf-8') as f:
                f.write(report)
        else:
            # Just show summary
            if not analyzed_news:
                print(f"No news analyzed for {args.symbol}")
                return
            
            positive = sum(1 for item in analyzed_news if item['sentiment'] == 'Positive')
            negative = sum(1 for item in analyzed_news if item['sentiment'] == 'Negative')
            neutral = sum(1 for item in analyzed_news if item['sentiment'] == 'Neutral')
            avg_score = sum(item['score'] for item in analyzed_news) / len(analyzed_news)
            
            print(f"Sentiment Analysis Summary for {args.symbol.upper()}:")
            print(f"Positive: {positive} | Negative: {negative} | Neutral: {neutral}")
            print(f"Average Sentiment Score: {avg_score:.2f}")

if __name__ == "__main__":
    main()