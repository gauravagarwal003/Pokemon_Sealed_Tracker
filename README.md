# TCGPlayer Pokemon Price Tracker

A Python script to scrape Pokemon sealed products from TCGPlayer.com.

## Setup

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the scraper:
```bash
python tcgplayer_scraper.py
```

The script will:
- Scrape Pokemon sealed products from TCGPlayer
- Extract product names, prices, images, and URLs
- Save the data to `pokemon_sealed_products.json`
- Display a summary of the scraped products

## Features

- Respectful scraping with delays between requests
- Error handling for network issues
- JSON output for further processing
- Configurable number of pages to scrape

## Notes

- The script includes proper headers to avoid being blocked
- Web scraping may break if TCGPlayer changes their website structure
- Be respectful of the website's terms of service and rate limits

## Output

The script generates a JSON file with the following structure:
```json
[
  {
    "name": "Product Name",
    "price": "$XX.XX",
    "image_url": "https://...",
    "product_url": "https://...",
    "availability": "In Stock",
    "set_name": "Set Name"
  }
]
```
