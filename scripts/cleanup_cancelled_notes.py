#!/usr/bin/env python3
"""
Clean up transaction notes by removing all "CANCELLED:" entries
This removes cancellation audit trail text while preserving original notes
"""

from db_utils import get_db_connection
from sqlalchemy import text
import re

def cleanup_cancelled_notes():
    """Remove all 'CANCELLED:' entries from transaction notes"""
    
    print("🧹 Cleaning up CANCELLED notes from transaction database...")
    
    try:
        with get_db_connection() as conn:
            # First, find all transactions with CANCELLED notes
            find_query = text("""
                SELECT transaction_id, merchant, notes
                FROM transactions 
                WHERE notes LIKE '%CANCELLED%'
                ORDER BY transaction_id
            """)
            
            cancelled_txns = conn.execute(find_query).fetchall()
            print(f"📊 Found {len(cancelled_txns)} transactions with CANCELLED notes")
            
            if len(cancelled_txns) == 0:
                print("✅ No CANCELLED notes found. Database is already clean!")
                return True, "No cleanup needed"
            
            print("\n🔍 Transactions that will be cleaned:")
            cleaned_count = 0
            
            for txn in cancelled_txns:
                transaction_id, merchant, original_notes = txn
                
                if original_notes:
                    # Clean the notes by removing CANCELLED entries
                    cleaned_notes = clean_notes_text(original_notes)
                    
                    print(f"\n📝 ID {transaction_id} - {merchant}:")
                    print(f"   BEFORE: {original_notes[:100]}...")
                    print(f"   AFTER:  {cleaned_notes[:100] if cleaned_notes else '(empty)'}...")
                    
                    # Update the transaction
                    update_query = text("""
                        UPDATE transactions 
                        SET notes = :new_notes
                        WHERE transaction_id = :txn_id
                    """)
                    
                    result = conn.execute(update_query, {
                        'new_notes': cleaned_notes if cleaned_notes else None,
                        'txn_id': transaction_id
                    })
                    
                    if result.rowcount > 0:
                        cleaned_count += 1
            
            # Commit all changes
            conn.commit()
            print(f"\n💾 Committed {cleaned_count} note updates")
            
            # Verify cleanup
            verify_query = text("""
                SELECT COUNT(*) as count
                FROM transactions 
                WHERE notes LIKE '%CANCELLED%'
            """)
            
            remaining_count = conn.execute(verify_query).fetchone()[0]
            
            if remaining_count == 0:
                print("✅ Cleanup successful! No CANCELLED notes remain.")
            else:
                print(f"⚠️  {remaining_count} transactions still have CANCELLED notes")
            
            # Show sample of cleaned transactions
            print("\n📋 Sample of cleaned transactions:")
            sample_query = text("""
                SELECT transaction_id, merchant, notes
                FROM transactions 
                WHERE transaction_id IN (
                    SELECT transaction_id FROM (
                        VALUES (%s), (%s), (%s)
                    ) AS t(transaction_id)
                )
            """ % (cancelled_txns[0][0], 
                   cancelled_txns[min(1, len(cancelled_txns)-1)][0], 
                   cancelled_txns[min(2, len(cancelled_txns)-1)][0]))
            
            sample_results = conn.execute(sample_query).fetchall()
            for row in sample_results:
                notes_preview = row[2][:60] + "..." if row[2] and len(row[2]) > 60 else row[2] or "(no notes)"
                print(f"   ID {row[0]}: {row[1]} - {notes_preview}")
            
            return True, f"Successfully cleaned {cleaned_count} transaction notes"
            
    except Exception as e:
        error_msg = f"Error cleaning cancelled notes: {e}"
        print(f"❌ {error_msg}")
        return False, error_msg

def clean_notes_text(notes):
    """Clean a notes string by removing CANCELLED entries"""
    
    if not notes:
        return None
    
    # Split by newlines to process each line
    lines = notes.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip lines that start with "CANCELLED:"
        if line.startswith('CANCELLED:'):
            continue
            
        # Keep non-empty lines that don't start with CANCELLED
        if line:
            cleaned_lines.append(line)
    
    # Join remaining lines
    cleaned_text = '\n'.join(cleaned_lines).strip()
    
    # Return None if no content remains
    return cleaned_text if cleaned_text else None

def preview_cleanup():
    """Preview what will be cleaned without making changes"""
    
    print("👀 PREVIEW MODE - No changes will be made")
    print("=" * 60)
    
    try:
        with get_db_connection() as conn:
            # Find transactions with CANCELLED notes
            find_query = text("""
                SELECT transaction_id, merchant, notes
                FROM transactions 
                WHERE notes LIKE '%CANCELLED%'
                ORDER BY transaction_id
                LIMIT 10
            """)
            
            cancelled_txns = conn.execute(find_query).fetchall()
            print(f"📊 Found {len(cancelled_txns)} transactions with CANCELLED notes")
            
            if len(cancelled_txns) == 0:
                print("✅ No CANCELLED notes found!")
                return
            
            print("\n🔍 Preview of what will be cleaned:")
            
            for txn in cancelled_txns:
                transaction_id, merchant, original_notes = txn
                
                if original_notes:
                    cleaned_notes = clean_notes_text(original_notes)
                    
                    print(f"\n📝 ID {transaction_id} - {merchant}:")
                    print(f"   CURRENT: {original_notes}")
                    print(f"   CLEANED: {cleaned_notes or '(empty)'}")
            
            if len(cancelled_txns) == 10:
                # Count total
                count_query = text("SELECT COUNT(*) FROM transactions WHERE notes LIKE '%CANCELLED%'")
                total_count = conn.execute(count_query).fetchone()[0]
                if total_count > 10:
                    print(f"\n... and {total_count - 10} more transactions")
                    
    except Exception as e:
        print(f"❌ Error during preview: {e}")

if __name__ == "__main__":
    print("🧹 Transaction Notes Cleanup Tool")
    print("=" * 60)
    
    # Test connection first
    try:
        from db_utils import test_connection
        success, msg = test_connection()
        if not success:
            print(f"❌ Database connection failed: {msg}")
            exit(1)
        print(f"✅ Database connection: {msg}")
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        exit(1)
    
    # Ask user what they want to do
    print("\nChoose an option:")
    print("1. Preview cleanup (no changes)")
    print("2. Clean up CANCELLED notes")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        preview_cleanup()
    elif choice == '2':
        confirm = input("\n⚠️  This will permanently remove CANCELLED notes. Continue? (y/N): ")
        if confirm.lower() == 'y':
            success, message = cleanup_cancelled_notes()
            
            if success:
                print(f"\n🎉 {message}")
                print("\n💡 Your transaction notes are now clean!")
            else:
                print(f"\n❌ Cleanup failed: {message}")
        else:
            print("👋 Cleanup cancelled")
    elif choice == '3':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")
