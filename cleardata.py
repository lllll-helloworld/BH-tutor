# clear_data.py
# clear_data.py
from database import get_db_connection

def clear_all_data():
    """Clear all data in the database and reset IDs"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            print("Cleaning database...")
            
            # 1. Temporarily disable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            
            # 2. Clear table data and reset IDs (AUTO_INCREMENT)
            cursor.execute("TRUNCATE TABLE wrong_questions;")
            print("  - Wrong question records cleared")
            
            # [New] Clear knowledge point score table
            cursor.execute("TRUNCATE TABLE user_topic_scores;")
            print("  - Knowledge point score records cleared")
            
            cursor.execute("TRUNCATE TABLE users;")
            print("  - User information cleared")
            
            # 3. Re-enable foreign key checks to restore safety mechanism
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            
        conn.commit()
        print("✅ Database cleaned successfully! Everything restored to factory settings.")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("⚠️  Warning: This operation will permanently delete all users, knowledge point distribution scores, and wrong question records!")
    confirm = input("Are you sure you want to continue? (enter y to proceed, any other key to cancel): ")
    
    if confirm.lower() == 'y':
        clear_all_data()
    else:
        print("Cleanup operation cancelled.")