import sys
import os
import json
import re
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    from data_fetcher import FinancialDataFetcher
except ImportError as e:
    print(f"Failed to import data_fetcher: {e}")
    sys.exit(1)

# We will read translations.ts to get all the existing keys
existing_keys = set()
try:
    with open('web/src/translations.ts', 'r', encoding='utf-8') as f:
        content = f.read()
        matches = re.finditer(r"'([a-zA-Z0-9_]+)'\s*:\s*\{", content)
        for m in matches:
            existing_keys.add(m.group(1))
except Exception as e:
    print(f"Failed reading translations.ts: {e}")

print(f"Loaded {len(existing_keys)} existing translation keys.")

tickers_to_test = [
    # US
    "AAPL", "MSFT", "AMZN", "JNJ", "JPM", "TSLA", "XOM", "DIS", "WMT", "NVDA",
    # HK
    "0700.HK", "9988.HK", "3690.HK", "0005.HK", "1299.HK", "0941.HK", "0011.HK", "1211.HK", "0386.HK", "0883.HK",
    # A-Share
    "600519", "601318", "000858", "300750", "002594", "600276", "600900", "000333", "600036", "601166"
]

missing_keys = set()
missing_examples = {}

import threading
import _thread

def quit_function(fn_name):
    print(f"{fn_name} took too long", file=sys.stderr)
    _thread.interrupt_main()

def timeout_decorator(s):
    def outer(fn):
        def inner(*args, **kwargs):
            timer = threading.Timer(s, quit_function, args=[fn.__name__])
            timer.start()
            try:
                result = fn(*args, **kwargs)
            finally:
                timer.cancel()
            return result
        return inner
    return outer

@timeout_decorator(10)
def fetch_data(ticker):
    return FinancialDataFetcher.get_financial_data(ticker)

for ticker in tickers_to_test:
    print(f"Fetching data for {ticker}...")
    try:
        statements = fetch_data(ticker)
        found_data = False
        
        for stmt_type in ['income_stmt', 'balance_sheet', 'cashflow']:
            if stmt_type in statements and isinstance(statements[stmt_type], dict):
                found_data = True
                for key in statements[stmt_type].keys():
                    norm_key = re.sub(r'\s+', '_', key.strip().lower())
                    if norm_key not in existing_keys:
                        missing_keys.add(norm_key)
                        if norm_key not in missing_examples:
                            missing_examples[norm_key] = key

        if not found_data and 'cn_income' in statements:
            for stmt_type in ['cn_income', 'cn_balance', 'cn_cash']:
                if stmt_type in statements and isinstance(statements[stmt_type], dict):
                    for key in statements[stmt_type].keys():
                        norm_key = re.sub(r'\s+', '_', key.strip().lower())
                        if norm_key not in existing_keys:
                            missing_keys.add(norm_key)
                            if norm_key not in missing_examples:
                                missing_examples[norm_key] = key

    except KeyboardInterrupt:
        print(f"Timeout fetching {ticker}, skipping...")
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
    
    time.sleep(1)

print(f"\n--- Found {len(missing_keys)} Missing Translation Keys ---")
output_lines = []
for norm_key in sorted(missing_keys):
    original = missing_examples[norm_key]
    output_lines.append(f"    '{norm_key}': {{ 'en': '{original}', 'zh-CN': '', 'zh-TW': '', 'ja': '' }},")

with open('missing_translations.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print("Saved to web/missing_translations.txt")
