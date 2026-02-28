# update_score.py
# change_score.py
from database import get_db_connection

def set_user_topic_score(username: str, topic: str, new_score: int):
    """Manually modify the score of a specified user for a specified knowledge point"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Verify user exists and get id
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if not user:
                print(f"❌ No record found for username '{username}'.")
                return
            
            user_id = user['id']
            
            # 2. Get current score for this knowledge point (default 500 if not present)
            cursor.execute("SELECT score FROM user_topic_scores WHERE user_id = %s AND topic = %s", (user_id, topic))
            old_record = cursor.fetchone()
            old_score = old_record['score'] if old_record else 500
            
            # 3. Insert or update new score
            sql = """
            INSERT INTO user_topic_scores (user_id, topic, score) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE score = VALUES(score)
            """
            cursor.execute(sql, (user_id, topic, new_score))
            conn.commit()
            
            print(f"✅ Success! User '{username}' score for topic【{topic}】has been changed from {old_score} to {new_score}.")
            
    except Exception as e:
        print(f"❌ Error occurred while updating database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=== 🛠️ Internal user knowledge point score modification tool ===")
    target_username = input("👉 Enter username to modify score: ").strip()
    
    if target_username:
        target_topic = input("👉 Enter knowledge point name (e.g. 'Basic Syntax' or 'Comprehensive'): ").strip()
        if not target_topic:
            print("❌ Knowledge point cannot be empty!")
        else:
            try:
                target_score = int(input(f"👉 Enter new score for {target_username} in【{target_topic}】(recommended 0-1000): "))
                
                # Double confirm to prevent misoperation
                confirm = input(f"⚠️ Are you sure you want to forcefully set '{target_username}'‘s score for【{target_topic}】to {target_score}? (y/n): ")
                if confirm.lower() == 'y':
                    set_user_topic_score(target_username, target_topic, target_score)
                else:
                    print("Operation cancelled.")
                    
            except ValueError:
                print("❌ Error: Score must be an integer!")
    else:
        print("❌ Username cannot be empty!")