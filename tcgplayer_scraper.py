#!/usr/bin/env python3
"""
TCGPlayer Pokemon Sealed Products Scraper

This script scrapes Pokemon sealed products from TCGPlayer.com
and extracts product information including names, prices, and availability.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Optional
import urllib.parse


class TCGPlayerScraper:
    def __init__(self):
        self.base_url = "https://www.tcgplayer.com"
        self.session = requests.Session()
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a webpage
        
        Args:
            url: The URL to fetch
            
        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            print(f"Fetching: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
            
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    def extract_product_info(self, product_element) -> Dict:
        """
        Extract product information from a product element
        
        Args:
            product_element: BeautifulSoup element containing product data
            
        Returns:
            Dictionary with product information
        """
        product_info = {
            'name': '',
            'price': '',
            'image_url': '',
            'product_url': '',
            'availability': '',
            'set_name': ''
        }
        
        try:
            # Extract product name
            name_elem = product_element.find('span', class_='product-card__title') or \
                       product_element.find('a', class_='product-card__title')
            if name_elem:
                product_info['name'] = name_elem.get_text(strip=True)
            
            # Extract price
            price_elem = product_element.find('span', class_='product-card__market-price') or \
                        product_element.find('div', class_='product-card__market-price')
            if price_elem:
                product_info['price'] = price_elem.get_text(strip=True)
            
            # Extract image URL
            img_elem = product_element.find('img')
            if img_elem and img_elem.get('src'):
                product_info['image_url'] = img_elem['src']
            
            # Extract product URL
            link_elem = product_element.find('a')
            if link_elem and link_elem.get('href'):
                product_info['product_url'] = self.base_url + link_elem['href']
            
            # Extract set information
            set_elem = product_element.find('span', class_='product-card__set-name')
            if set_elem:
                product_info['set_name'] = set_elem.get_text(strip=True)
                
        except Exception as e:
            print(f"Error extracting product info: {e}")
        
        return product_info
    
    def scrape_pokemon_sealed_products(self, page: int = 1, max_pages: int = 5) -> List[Dict]:
        """
        Scrape Pokemon sealed products from TCGPlayer
        
        Args:
            page: Starting page number
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of product dictionaries
        """
        products = []
        
        for current_page in range(page, page + max_pages):
            # Construct the URL
            url = (f"https://www.tcgplayer.com/search/pokemon/product?"
                   f"productLineName=pokemon&page={current_page}&view=grid&"
                   f"ProductTypeName=Sealed+Products")
            
            # Get the page
            soup = self.get_page(url)
            if not soup:
                print(f"Failed to load page {current_page}")
                continue
            
            # Find product containers - these class names might need adjustment
            product_containers = soup.find_all('div', class_='product-card') or \
                               soup.find_all('div', class_='search-result__content') or \
                               soup.find_all('article', class_='product-card')
            
            if not product_containers:
                print(f"No products found on page {current_page}")
                # Try alternative selectors
                product_containers = soup.find_all('div', {'data-testid': 'product-card'}) or \
                                   soup.find_all('div', class_='product-tile')
            
            print(f"Found {len(product_containers)} products on page {current_page}")
            
            # Extract product information
            for container in product_containers:
                product_info = self.extract_product_info(container)
                if product_info['name']:  # Only add if we found a name
                    products.append(product_info)
            
            # Be respectful - add a delay between requests
            time.sleep(1)
        
        return products
    
    def save_products_to_json(self, products: List[Dict], filename: str = 'pokemon_sealed_products.json'):
        """
        Save products to a JSON file
        
        Args:
            products: List of product dictionaries
            filename: Output filename
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(products)} products to {filename}")
        except Exception as e:
            print(f"Error saving to JSON: {e}")
    
    def print_products_summary(self, products: List[Dict]):
        """
        Print a summary of scraped products
        
        Args:
            products: List of product dictionaries
        """
        print(f"\n=== SCRAPED {len(products)} POKEMON SEALED PRODUCTS ===\n")
        
        for i, product in enumerate(products[:10], 1):  # Show first 10
            print(f"{i}. {product['name']}")
            print(f"   Price: {product['price']}")
            print(f"   Set: {product['set_name']}")
            print(f"   URL: {product['product_url']}")
            print()
        
        if len(products) > 10:
            print(f"... and {len(products) - 10} more products")


def main():
    """
    Main function to run the scraper
    """
    scraper = TCGPlayerScraper()
    
    print("Starting TCGPlayer Pokemon Sealed Products scraper...")
    
    # Scrape products (start with 2 pages to test)
    products = scraper.scrape_pokemon_sealed_products(page=1, max_pages=2)
    
    if products:
        # Print summary
        scraper.print_products_summary(products)
        
        # Save to JSON file
        scraper.save_products_to_json(products)
        
        print(f"\nScraping completed! Found {len(products)} products.")
    else:
        print("No products were scraped. The website structure might have changed.")
        print("You may need to inspect the page source and update the CSS selectors.")


if __name__ == "__main__":
    main()
