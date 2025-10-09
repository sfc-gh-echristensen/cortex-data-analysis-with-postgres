#!/usr/bin/env python3
"""
Generate expanded realistic transaction data
- PostgreSQL: 60 days of data (~240 transactions)  
- Snowflake: 1 year of data (~1200 transactions)
"""

import pandas as pd
import random
from datetime import datetime, timedelta
import csv

# Merchant data with realistic spending patterns
MERCHANTS = {
    'Groceries': {
        'merchants': ['Whole Foods Market', 'Kroger', 'Safeway', 'Trader Joe\'s', 'Walmart', 'Costco Wholesale', 'Publix', 'Aldi', 'Fresh Market', 'Stop & Shop'],
        'amounts': (15, 150),
        'frequency': 0.20  # 20% of all transactions
    },
    'Dining': {
        'merchants': ['Starbucks Coffee', 'McDonald\'s', 'Chipotle Mexican Grill', 'Subway', 'Panera Bread', 'Olive Garden', 'Cheesecake Factory', 'Taco Bell', 'KFC', 'Five Guys', 'In-N-Out Burger', 'Denny\'s', 'Applebee\'s', 'Red Lobster', 'Chili\'s'],
        'amounts': (8, 85),
        'frequency': 0.25  # 25% of all transactions
    },
    'Transportation': {
        'merchants': ['Shell Gas Station', 'Exxon Mobil', 'Chevron', 'BP Gas Station', 'Uber', 'Lyft'],
        'amounts': (15, 80),
        'frequency': 0.12
    },
    'Electronics': {
        'merchants': ['Best Buy Electronics', 'Apple Store', 'Microsoft Store', 'Samsung Store', 'Sony Store', 'Dell Technologies', 'HP Store', 'Lenovo Store', 'Canon Store', 'Nikon Store'],
        'amounts': (50, 1200),
        'frequency': 0.08
    },
    'Travel': {
        'merchants': ['Delta Airlines', 'United Airlines', 'Southwest Airlines', 'American Airlines', 'Hilton Hotels', 'Marriott', 'Best Western', 'Expedia', 'Booking.com', 'Kayak'],
        'amounts': (120, 800),
        'frequency': 0.06
    },
    'Shopping': {
        'merchants': ['Amazon.com', 'Target', 'Walmart', 'eBay', 'Macy\'s', 'Nordstrom', 'Gap', 'H&M', 'Zara', 'Forever 21'],
        'amounts': (20, 300),
        'frequency': 0.15
    },
    'Entertainment': {
        'merchants': ['Netflix', 'Spotify', 'AMC Theatres', 'GameStop', 'Redbox', 'Dave & Buster\'s', 'TopGolf'],
        'amounts': (10, 120),
        'frequency': 0.08
    },
    'Healthcare': {
        'merchants': ['CVS Pharmacy', 'Walgreens', 'Rite Aid', 'Kaiser Permanente', 'Quest Diagnostics'],
        'amounts': (15, 250),
        'frequency': 0.06
    }
}

def generate_transaction_date(start_date, end_date):
    """Generate a random date between start and end dates"""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)

def select_merchant_and_amount():
    """Select a random merchant and amount based on category frequencies"""
    
    # Create weighted list based on frequencies
    categories = []
    weights = []
    
    for category, data in MERCHANTS.items():
        categories.append(category)
        weights.append(data['frequency'])
    
    # Select category based on weights
    category = random.choices(categories, weights=weights)[0]
    category_data = MERCHANTS[category]
    
    # Select random merchant from category
    merchant = random.choice(category_data['merchants'])
    
    # Generate amount within range
    min_amt, max_amt = category_data['amounts']
    amount = round(random.uniform(min_amt, max_amt), 2)
    
    return merchant, category, amount

def generate_realistic_notes(merchant, category, amount):
    """Generate realistic transaction notes"""
    
    notes_templates = {
        'Groceries': ['Weekly shopping', 'Organic produce', 'Bulk items', 'Fresh ingredients', 'Household supplies'],
        'Dining': ['Quick lunch', 'Morning coffee', 'Dinner with family', 'Business lunch', 'Weekend treat'],
        'Transportation': ['Fill up tank', 'Ride to airport', 'Daily commute', 'Road trip fuel', 'Emergency ride'],
        'Electronics': ['Laptop upgrade', 'Phone repair', 'New headphones', 'Monitor purchase', 'Gaming gear'],
        'Travel': ['Business trip', 'Vacation booking', 'Weekend getaway', 'Flight change', 'Hotel stay'],
        'Shopping': ['Online order', 'Gift shopping', 'Seasonal sale', 'Home essentials', 'Clothing'],
        'Entertainment': ['Monthly subscription', 'Movie night', 'Game purchase', 'Date night', 'Weekend fun'],
        'Healthcare': ['Prescription refill', 'Doctor visit', 'Health supplements', 'Medical supplies', 'Checkup']
    }
    
    if category in notes_templates:
        return random.choice(notes_templates[category])
    else:
        return f"Purchase at {merchant}"

def generate_postgresql_data(num_days=60):
    """Generate PostgreSQL transaction data for specified number of days"""
    
    print(f"📊 Generating PostgreSQL data for {num_days} days...")
    
    # Date range: last N days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=num_days-1)
    
    transactions = []
    
    # Generate 3-5 transactions per day on average
    total_transactions = num_days * random.randint(3, 5)
    
    for i in range(total_transactions):
        # Generate transaction details
        date = generate_transaction_date(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time())
        )
        
        merchant, category, amount = select_merchant_and_amount()
        notes = generate_realistic_notes(merchant, category, amount)
        
        # Random status (most approved, few pending for testing)
        if i < 4:  # First 4 transactions as pending for testing
            status = 'pending'
        else:
            status = 'approved'
        
        transactions.append({
            'date': date.strftime('%Y-%m-%d %H:%M:%S'),
            'amount': amount,
            'merchant': merchant,
            'category': category,
            'notes': notes,
            'status': status,
            'account_id': 1
        })
    
    # Sort by date
    transactions.sort(key=lambda x: x['date'])
    
    print(f"✅ Generated {len(transactions)} PostgreSQL transactions")
    return transactions

def generate_snowflake_data(num_days=365):
    """Generate Snowflake transaction data for specified number of days"""
    
    print(f"📊 Generating Snowflake data for {num_days} days...")
    
    # Date range: last N days  
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=num_days-1)
    
    transactions = []
    accounts = ['Checking', 'Credit Card', 'Savings']
    
    # Generate 2-4 transactions per day on average
    total_transactions = num_days * random.randint(2, 4)
    
    for i in range(total_transactions):
        # Generate transaction details
        date = generate_transaction_date(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time())
        )
        
        merchant, category, amount = select_merchant_and_amount()
        account_name = random.choice(accounts)
        
        transactions.append({
            'transaction_id': f'tx-{3000 + i:04d}',
            'date': date.strftime('%Y-%m-%d'),
            'account_name': account_name,
            'amount': amount,
            'category': category,
            'merchant': merchant
        })
    
    # Sort by date
    transactions.sort(key=lambda x: x['date'])
    
    print(f"✅ Generated {len(transactions)} Snowflake transactions")
    return transactions

def save_csv(data, filename, fieldnames):
    """Save data to CSV file"""
    
    print(f"💾 Saving {len(data)} records to {filename}")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ Saved {filename}")

def main():
    """Generate both PostgreSQL and Snowflake datasets"""
    
    print("🏭 Expanded Transaction Data Generator")
    print("=" * 60)
    
    # Generate PostgreSQL data (60 days)
    print("\n🐘 PostgreSQL Dataset:")
    pg_data = generate_postgresql_data(60)
    pg_fieldnames = ['date', 'amount', 'merchant', 'category', 'notes', 'status', 'account_id']
    save_csv(pg_data, 'expanded_transactions_postgresql.csv', pg_fieldnames)
    
    # Show PostgreSQL summary
    pending_count = sum(1 for t in pg_data if t['status'] == 'pending')
    approved_count = sum(1 for t in pg_data if t['status'] == 'approved')
    total_amount = sum(t['amount'] for t in pg_data)
    
    print(f"   📊 PostgreSQL Summary:")
    print(f"      - Total: {len(pg_data)} transactions")
    print(f"      - Pending: {pending_count} transactions")
    print(f"      - Approved: {approved_count} transactions")
    print(f"      - Total Value: ${total_amount:,.2f}")
    print(f"      - Date Range: {pg_data[0]['date'][:10]} to {pg_data[-1]['date'][:10]}")
    
    # Generate Snowflake data (1 year)
    print("\n❄️ Snowflake Dataset:")
    sf_data = generate_snowflake_data(365)
    sf_fieldnames = ['transaction_id', 'date', 'account_name', 'amount', 'category', 'merchant']
    save_csv(sf_data, 'expanded_transactions_snowflake.csv', sf_fieldnames)
    
    # Show Snowflake summary
    sf_total_amount = sum(t['amount'] for t in sf_data)
    sf_categories = len(set(t['category'] for t in sf_data))
    sf_merchants = len(set(t['merchant'] for t in sf_data))
    
    print(f"   📊 Snowflake Summary:")
    print(f"      - Total: {len(sf_data)} transactions")
    print(f"      - Total Value: ${sf_total_amount:,.2f}")
    print(f"      - Categories: {sf_categories}")
    print(f"      - Merchants: {sf_merchants}")
    print(f"      - Date Range: {sf_data[0]['date']} to {sf_data[-1]['date']}")
    
    print("\n🎉 Data generation complete!")
    print("\n📁 Files created:")
    print("   - expanded_transactions_postgresql.csv")
    print("   - expanded_transactions_snowflake.csv")
    
    print("\n💡 Next steps:")
    print("   1. Run: python3 update_transaction_status.py")
    print("   2. Load PostgreSQL: python3 bulk_insert_sample_data.py")
    print("   3. Load Snowflake: python3 bulk_insert_snowflake_data.py")

if __name__ == "__main__":
    main()
