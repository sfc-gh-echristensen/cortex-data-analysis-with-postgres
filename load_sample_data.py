#!/usr/bin/env python3
"""
Load sample transaction data into both PostgreSQL and Snowflake
Combines functionality for both databases with menu selection
"""

import sys
from bulk_insert_sample_data import bulk_insert_transactions, show_transaction_summary
from bulk_insert_snowflake_data import bulk_insert_snowflake_transactions, show_snowflake_summary

def show_menu():
    """Display database selection menu"""
    print("🗂️ Sample Data Loader")
    print("=" * 50)
    print("Choose which database to load data into:")
    print("1. PostgreSQL (60 transactions)")  
    print("2. Snowflake (100 transactions)")
    print("3. Both databases")
    print("4. Exit")
    print("-" * 50)

def main():
    """Main menu handler"""
    
    while True:
        show_menu()
        
        try:
            choice = input("Enter your choice (1-4): ").strip()
            
            if choice == '1':
                print("\n🐘 Loading data into PostgreSQL...")
                success, message = bulk_insert_transactions()
                
                if success:
                    print(f"✅ {message}")
                    show_transaction_summary()
                else:
                    print(f"❌ PostgreSQL insert failed: {message}")
                    
            elif choice == '2':
                print("\n❄️ Loading data into Snowflake...")
                success, message = bulk_insert_snowflake_transactions()
                
                if success:
                    print(f"✅ {message}")
                    show_snowflake_summary()
                else:
                    print(f"❌ Snowflake insert failed: {message}")
                    
            elif choice == '3':
                print("\n🔄 Loading data into both databases...")
                
                # PostgreSQL first
                print("\n🐘 Step 1: PostgreSQL...")
                pg_success, pg_message = bulk_insert_transactions()
                
                if pg_success:
                    print(f"✅ PostgreSQL: {pg_message}")
                else:
                    print(f"❌ PostgreSQL failed: {pg_message}")
                
                # Snowflake second
                print("\n❄️ Step 2: Snowflake...")
                sf_success, sf_message = bulk_insert_snowflake_transactions()
                
                if sf_success:
                    print(f"✅ Snowflake: {sf_message}")
                else:
                    print(f"❌ Snowflake failed: {sf_message}")
                
                # Summary
                if pg_success and sf_success:
                    print("\n🎉 Both databases loaded successfully!")
                    print("\n📊 Summary:")
                    show_transaction_summary()
                    show_snowflake_summary()
                elif pg_success or sf_success:
                    print("\n⚠️ Partial success - one database loaded")
                else:
                    print("\n❌ Both database loads failed")
                    
            elif choice == '4':
                print("\n👋 Goodbye!")
                break
                
            else:
                print("\n❌ Invalid choice. Please enter 1, 2, 3, or 4.")
                
            # Wait for user before showing menu again
            if choice in ['1', '2', '3']:
                input("\nPress Enter to continue...")
                print("\n" + "="*60)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()
