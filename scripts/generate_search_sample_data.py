#!/usr/bin/env python3
"""
Generate sample transaction data optimized for search demonstration.

This creates transactions that showcase the differences between:
1. ILIKE pattern matching (exact substring matches)
2. pg_trgm fuzzy search (typo tolerance, similarity)  
3. pgvector semantic search (conceptual similarity)
"""

import random
import csv
from datetime import datetime, timedelta
from decimal import Decimal

# Sample data designed to showcase different search capabilities
SEARCH_OPTIMIZED_TRANSACTIONS = [
    # Coffee variations - show exact vs fuzzy vs semantic matching
    ("Starbucks Downtown", "Premium coffee and pastry", 12.45, "Food & Dining"),
    ("Starbuks Main St", "Morning coffe latte", 8.95, "Food & Dining"),  # Typos for fuzzy search
    ("Local Cafe Corner", "Artisan espresso drink", 6.50, "Food & Dining"),  # Semantic: coffee concept
    ("Bean There Coffee", "Cappuccino and muffin", 9.25, "Food & Dining"),
    ("Coffee Shop Express", "Iced coffee regular", 4.75, "Food & Dining"),
    ("Morning Brew Co", "Hot beverage and snack", 7.80, "Food & Dining"),  # Semantic: morning drink
    ("Cafe Mocha Place", "Specialty coffee blend", 11.30, "Food & Dining"),
    ("Daily Grind Cofee", "Caffeine fix latte", 5.95, "Food & Dining"),  # Typo: Cofee
    
    # Grocery/Food variations
    ("Whole Foods Market", "Organic grocery shopping", 89.47, "Food & Dining"),
    ("Whoel Foods", "Weekly grocery run", 76.82, "Food & Dining"),  # Typo
    ("Fresh Market Co", "Produce and essentials", 45.67, "Food & Dining"),  # Semantic: grocery
    ("Safeway Supermarket", "Food and household items", 112.34, "Food & Dining"),
    ("Trader Joes", "Specialty food shopping", 67.89, "Food & Dining"),  # Missing apostrophe
    ("Local Farmers Market", "Fresh vegetables and fruit", 34.56, "Food & Dining"),  # Semantic
    ("Costco Wholesale", "Bulk food purchase", 156.78, "Food & Dining"),
    ("Target Groceries", "Weekly food supplies", 78.90, "Food & Dining"),  # Semantic
    
    # Transportation variations
    ("Uber Technologies", "Rideshare to airport", 45.60, "Transportation"),
    ("Uberr Tech", "Ride to downtown", 23.40, "Transportation"),  # Typo
    ("Lyft Inc", "Quick ride home", 18.75, "Transportation"),
    ("Yellow Cab Co", "Taxi service fare", 32.10, "Transportation"),  # Semantic: ride
    ("City Metro Transit", "Public transportation", 12.50, "Transportation"),  # Semantic
    ("Airport Shuttle", "Travel to terminal", 28.00, "Transportation"),  # Semantic
    ("Parking Meter", "Downtown parking fee", 8.00, "Transportation"),
    ("Gas Station Shell", "Vehicle fuel purchase", 67.45, "Transportation"),  # Semantic
    
    # Subscription services
    ("Netflix Streaming", "Monthly video subscription", 15.99, "Entertainment"),
    ("Netflx", "Monthly streaming service", 15.99, "Entertainment"),  # Typo
    ("Spotify Premium", "Music subscription monthly", 9.99, "Entertainment"),
    ("Spotfy Premium", "Music streaming plan", 9.99, "Entertainment"),  # Typo
    ("Adobe Creative Suite", "Design software subscription", 52.99, "Utilities"),
    ("YouTube Premium", "Ad-free video service", 11.99, "Entertainment"),
    ("Amazon Prime Video", "Streaming service plan", 8.99, "Entertainment"),  # Semantic: streaming
    ("Hulu Plus", "Television streaming", 12.99, "Entertainment"),  # Semantic
    
    # Shopping variations
    ("Amazon Purchase", "Online shopping order", 89.76, "Shopping"),
    ("Amazn Purchase", "Online order delivery", 45.32, "Shopping"),  # Typo
    ("eBay Marketplace", "Auction site purchase", 67.89, "Shopping"),
    ("Best Buy Electronics", "Tech gadget shopping", 234.56, "Shopping"),
    ("Apple Store Online", "Device and accessories", 899.00, "Shopping"),
    ("Target Corporation", "Retail store shopping", 78.45, "Shopping"),
    ("Walmart Supercenter", "General merchandise", 56.78, "Shopping"),
    ("Home Depot Store", "Hardware and tools", 145.67, "Shopping"),  # Semantic: retail
    
    # Fitness & Health
    ("Planet Fitness Gym", "Monthly gym membership", 22.99, "Health & Fitness"),
    ("Planett Fitness", "Gym membership fee", 22.99, "Health & Fitness"),  # Typo
    ("LA Fitness Club", "Fitness center access", 39.99, "Health & Fitness"),
    ("Yoga Studio Downtown", "Wellness class package", 85.00, "Health & Fitness"),  # Semantic: fitness
    ("CrossFit Box", "Training session fee", 150.00, "Health & Fitness"),  # Semantic
    ("Running Store", "Athletic gear purchase", 89.99, "Health & Fitness"),  # Semantic
    ("Nutrition Supplements", "Health supplement order", 67.50, "Health & Fitness"),  # Semantic
    
    # Utilities & Services
    ("Pacific Gas Electric", "Monthly utility bill", 145.67, "Utilities"),
    ("PG&E Utility", "Electricity service", 132.45, "Utilities"),  # Semantic: same company
    ("Comcast Internet", "Broadband service monthly", 79.99, "Utilities"),
    ("Verizon Wireless", "Mobile phone service", 85.50, "Utilities"),
    ("Water Department", "Municipal water bill", 67.80, "Utilities"),  # Semantic: utility
    ("Waste Management", "Garbage collection fee", 45.20, "Utilities"),  # Semantic
    ("AT&T Mobility", "Cell phone plan", 92.10, "Utilities"),
    
    # Restaurants (various cuisines for semantic testing)
    ("Italian Bistro Roma", "Authentic pasta dinner", 67.89, "Food & Dining"),
    ("Sushi Zen Restaurant", "Japanese cuisine meal", 89.45, "Food & Dining"),
    ("Taco Bell Fast Food", "Mexican quick meal", 12.67, "Food & Dining"),
    ("Pizza Hut Delivery", "Italian food delivery", 28.90, "Food & Dining"),  # Semantic: Italian
    ("Thai Garden Restaurant", "Asian cuisine dinner", 45.60, "Food & Dining"),  # Semantic: Asian
    ("Burger King Fast", "Quick burger meal", 9.87, "Food & Dining"),  # Semantic: fast food
    ("Fine Dining Steakhouse", "Upscale dinner experience", 156.78, "Food & Dining"),  # Semantic: restaurant
    
    # Travel & Hotels
    ("Marriott Hotel", "Business travel lodging", 189.99, "Travel"),
    ("Marriot Hotel", "Hotel accommodation", 167.45, "Travel"),  # Typo
    ("Airbnb Rental", "Vacation home stay", 245.00, "Travel"),
    ("Delta Airlines", "Flight ticket purchase", 567.89, "Travel"),
    ("United Airlines", "Air travel booking", 489.50, "Travel"),  # Semantic: airline
    ("Hotel Booking Site", "Accommodation reservation", 178.90, "Travel"),  # Semantic: lodging
    ("Rental Car Agency", "Vehicle rental fee", 234.56, "Travel"),  # Semantic: travel
    
    # Financial Services
    ("Bank of America", "Monthly service charge", 12.00, "Banking"),
    ("Wells Fargo Bank", "ATM withdrawal fee", 3.50, "Banking"),
    ("Chase Bank Fee", "Account maintenance", 15.00, "Banking"),  # Semantic: banking
    ("Credit Union", "Member service charge", 5.00, "Banking"),  # Semantic: financial
    ("Investment Advisor", "Financial planning fee", 200.00, "Banking"),  # Semantic
    
    # Entertainment venues
    ("AMC Movie Theater", "Cinema ticket and snacks", 34.50, "Entertainment"),
    ("Regal Cinemas", "Movie screening ticket", 16.75, "Entertainment"),  # Semantic: cinema
    ("Concert Hall Venue", "Live music performance", 89.00, "Entertainment"),  # Semantic: entertainment
    ("Sports Stadium", "Game ticket purchase", 125.00, "Entertainment"),  # Semantic
    ("Art Museum", "Cultural exhibition visit", 25.00, "Entertainment"),  # Semantic
]

def generate_search_optimized_csv(filename="search_optimized_transactions.csv", num_base_transactions=100):
    """Generate CSV with search-optimized transaction data."""
    
    transactions = []
    start_date = datetime.now() - timedelta(days=90)
    
    # Add our carefully crafted search test transactions
    for i, (merchant, description, amount, category) in enumerate(SEARCH_OPTIMIZED_TRANSACTIONS, 1):
        # Generate dates over the past 90 days
        days_ago = random.randint(0, 89)
        transaction_date = start_date + timedelta(days=days_ago)
        
        transactions.append({
            'transaction_id': 9000 + i,  # Start from 9000 to avoid conflicts
            'account_name': random.choice(['Checking', 'Credit Card', 'Savings']),
            'date': transaction_date.strftime('%Y-%m-%d'),
            'amount': amount,
            'merchant': merchant,
            'description': description,
            'category': category,
            'status': 'approved'
        })
    
    # Add some additional random transactions to fill out the dataset
    random_merchants = [
        "Generic Store", "Online Retailer", "Local Business", "Service Provider",
        "Restaurant Chain", "Gas Station", "Pharmacy", "Electronics Store"
    ]
    
    random_categories = [
        "Food & Dining", "Shopping", "Transportation", "Entertainment", 
        "Utilities", "Health & Fitness", "Travel", "Banking"
    ]
    
    for i in range(len(SEARCH_OPTIMIZED_TRANSACTIONS) + 1, num_base_transactions + 1):
        days_ago = random.randint(0, 89)
        transaction_date = start_date + timedelta(days=days_ago)
        
        merchant = random.choice(random_merchants)
        category = random.choice(random_categories)
        amount = round(random.uniform(5.00, 200.00), 2)
        
        transactions.append({
            'transaction_id': 9000 + i,  # Continue from search transactions
            'account_name': random.choice(['Checking', 'Credit Card', 'Savings']),
            'date': transaction_date.strftime('%Y-%m-%d'),
            'amount': amount,
            'merchant': merchant,
            'description': f'{category.lower()} purchase at {merchant}',
            'category': category,
            'status': 'approved'
        })
    
    # Write to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['transaction_id', 'account_name', 'date', 'amount', 'merchant', 'description', 'category', 'status']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for transaction in transactions:
            writer.writerow(transaction)
    
    print(f"Generated {len(transactions)} search-optimized transactions in {filename}")
    print("\nSearch test scenarios included:")
    print("✅ ILIKE tests: Exact matches for 'coffee', 'starbucks', 'netflix'")
    print("✅ pg_trgm tests: Typos like 'starbuks', 'cofee', 'netflx'") 
    print("✅ Semantic tests: 'morning drink' → coffee, 'streaming' → netflix")
    print("✅ Fuzzy matching: 'amazn' → amazon, 'planett' → planet")
    print("✅ Conceptual search: 'ride' → uber/lyft/taxi, 'fitness' → gym/yoga")

if __name__ == "__main__":
    generate_search_optimized_csv()
