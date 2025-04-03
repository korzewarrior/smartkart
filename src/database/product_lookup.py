#!/usr/bin/env python3
import requests
import json
import os
import logging
from datetime import datetime

class ProductInfoLookup:
    """
    Class for looking up product information from a barcode using external databases
    """
    def __init__(self, product_list_file="product_list.txt"):
        """
        Initialize the product lookup system
        
        Parameters:
        - product_list_file: Path to the file to store scanned products
        """
        # Set up logger
        self.logger = logging.getLogger("SmartKart.ProductLookup")
        
        # Configure allergens to look for
        self.allergens = [
            'peanuts', 'peanut', 'nuts', 'milk', 'dairy', 'eggs', 'egg', 
            'soy', 'wheat', 'gluten', 'fish', 'shellfish', 'sesame'
        ]
        
        # Track scanned product barcodes to avoid duplicates
        self.scanned_products = set()
        
        # Set product list file path
        self.product_list_file = product_list_file
        
        # Load existing product list if available
        self._load_existing_products()

    def _log(self, message):
        """Log a message to the file logger"""
        self.logger.info(message)

    def _load_existing_products(self):
        """
        Load existing products from the product list file to avoid duplicates
        """
        try:
            if os.path.exists(self.product_list_file):
                with open(self.product_list_file, 'r') as file:
                    for line in file:
                        if line.startswith('#') or line.startswith('-'):
                            continue  # Skip comment and header lines
                        parts = line.strip().split('|')
                        if len(parts) >= 1:
                            barcode = parts[0].strip()
                            if barcode and barcode.isdigit():
                                self.scanned_products.add(barcode)
                self._log(f"Loaded {len(self.scanned_products)} products from existing list")
        except Exception as e:
            self._log(f"Error loading existing product list: {e}")

    def track_product(self, barcode, product_name="Unknown", brand="Unknown"):
        """
        Add a product to the tracked products list
        
        Parameters:
        - barcode: The product barcode
        - product_name: The product name
        - brand: The product brand
        
        Returns:
        - True if the product was added, False if it already existed
        """
        # Make sure we have data directory
        product_list_dir = os.path.dirname(self.product_list_file)
        if product_list_dir and not os.path.exists(product_list_dir):
            os.makedirs(product_list_dir, exist_ok=True)
            
        # Create file with header if it doesn't exist
        if not os.path.exists(self.product_list_file):
            with open(self.product_list_file, 'w') as file:
                timestamp = datetime.now().strftime("%a %b %d %I:%M:%S %p %Z %Y")
                file.write(f"# Product List - Created {timestamp}\n")
            self._log(f"Created new product list file: {self.product_list_file}")
            
        # Skip if already scanned to prevent duplicates
        if barcode in self.scanned_products:
            self._log(f"Product {barcode} already in list - skipping")
            return False
            
        # Add to tracked products
        self.scanned_products.add(barcode)
        
        # Format the entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"{barcode} | {product_name} | {brand} | {timestamp}\n"
        
        # Append to product list file
        try:
            with open(self.product_list_file, 'a') as file:
                file.write(entry)
            self._log(f"Added product to tracking list: {barcode}")
            return True
        except Exception as e:
            self._log(f"Error adding product to list: {e}")
            return False
            
    def lookup_barcode(self, barcode):
        """
        Look up product information from a barcode
        
        Parameters:
        - barcode: The barcode number (EAN, UPC, etc.)
        
        Returns:
        - A dictionary with product information
        """
        # Look up in Open Food Facts API
        self._log(f"Looking up barcode {barcode} in Open Food Facts database...")
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('status') == 1:  # Success
                product_data = {
                    'found': True,
                    'barcode': barcode,
                    'product_name': data.get('product').get('product_name', 'Unknown product'),
                    'brand': data.get('product').get('brands', 'Unknown brand'),
                    'ingredients_text': data.get('product').get('ingredients_text', 'Ingredients not available'),
                    'allergens': data.get('product').get('allergens_tags', []),
                    'image_url': data.get('product').get('image_url', ''),
                    'nutrition_grades': data.get('product').get('nutrition_grades', ''),
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Clean up allergens format
                allergens = []
                for allergen in product_data['allergens']:
                    if allergen.startswith('en:'):
                        allergens.append(allergen[3:])
                    else:
                        allergens.append(allergen)
                product_data['allergens'] = allergens
                
                return product_data
            else:
                # Product not found
                product_data = {
                    'found': False,
                    'barcode': barcode,
                    'product_name': "Product not found",
                    'brand': "Unknown",
                    'message': 'Product not found in database',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                return product_data
                
        except requests.RequestException as e:
            self._log(f"Error looking up barcode: {e}")
            return {
                'found': False,
                'barcode': barcode,
                'product_name': "Error",
                'brand': "Unknown",
                'message': f'Error: {str(e)}',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
    def save_product_info(self, product_data, output_dir="scan_results"):
        """
        Save product information to a file
        
        Parameters:
        - product_data: The product information dictionary
        - output_dir: Directory to save product info
        
        Returns:
        - Path to the saved file, or None if save failed
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        barcode = product_data.get('barcode', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"{barcode}_{timestamp}.json")
        
        try:
            with open(filename, 'w') as file:
                json.dump(product_data, file, indent=2)
            self._log(f"Product info saved to {filename}")
            return filename
        except Exception as e:
            self._log(f"Error saving product info: {e}")
            return None

    def check_allergens(self, product_data):
        """
        Check if product contains common allergens
        
        Parameters:
        - product_data: Product information dictionary
        
        Returns:
        - List of found allergens
        """
        if not product_data.get('found', False):
            return []
            
        # Allergens may already be in the product data
        allergens = product_data.get('allergens', [])
        if allergens:
            return allergens
            
        # Otherwise, check the ingredients text
        ingredients_text = product_data.get('ingredients_text', '').lower()
        found_allergens = []
        
        for allergen in self.allergens:
            if allergen in ingredients_text and allergen not in found_allergens:
                found_allergens.append(allergen)
                
        return found_allergens

# Simple test function
def test_product_lookup():
    """
    Test function to demonstrate product lookup
    """
    # Configure logging to file
    logging.basicConfig(
        filename="product_lookup_test.log",
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    lookup = ProductInfoLookup()
    
    # Example barcodes to test
    test_barcodes = [
        "0012000161155",  # Coca-Cola
        "0049000006582",  # Pepsi
        "invalid_barcode"  # To test error handling
    ]
    
    for barcode in test_barcodes:
        print(f"\nLooking up barcode: {barcode}")
        product_data = lookup.lookup_barcode(barcode)
        
        if product_data.get('found', False):
            print(f"Product found: {product_data.get('product_name')} by {product_data.get('brand')}")
            
            # Check for allergens
            allergens = lookup.check_allergens(product_data)
            if allergens:
                print(f"Allergen warning: Contains {', '.join(allergens)}")
            else:
                print("No common allergens detected")
                
            # Save product info
            lookup.save_product_info(product_data)
            
            # Track the product
            lookup.track_product(
                barcode,
                product_data.get('product_name'),
                product_data.get('brand')
            )
        else:
            print(f"Product not found: {product_data.get('message', 'Unknown error')}")

if __name__ == "__main__":
    test_product_lookup() 