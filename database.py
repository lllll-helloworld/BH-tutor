# database.py
import pymysql
import bcrypt

DB_CONFIG = {
    'host': '127.0.0.1',      
    'user': 'root',           
    'password': 'root',       # Please keep your actual password
    'database': 'ai_tutor_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor 
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_user(username, plain_password):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return False, "Username already exists, please login directly or choose another username"
            
            sql = "INSERT INTO users (username, password_hash) VALUES (%s, %s)"
            cursor.execute(sql, (username, hash_password(plain_password)))
        conn.commit() 
        return True, "Registration successful"
    except Exception as e:
        return False, f"Registration failed: {e}"
    finally:
        conn.close()

def verify_user_login(username, plain_password):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, password_hash FROM users WHERE username = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()
            if user and verify_password(plain_password, user['password_hash']):
                return user['id']
        return None
    finally:
        conn.close()

def get_user_info(user_id: int) -> dict:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
    finally:
        conn.close()

# ================= Knowledge Point Score System =================

def get_topic_score(user_id: int, topic: str) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT score FROM user_topic_scores WHERE user_id = %s AND topic = %s"
            cursor.execute(sql, (user_id, topic))
            result = cursor.fetchone()
            return result['score'] if result else 500
    finally:
        conn.close()

def update_topic_score(user_id: int, topic: str, score_change: int) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql_insert = "INSERT IGNORE INTO user_topic_scores (user_id, topic, score) VALUES (%s, %s, 500)"
            cursor.execute(sql_insert, (user_id, topic))

            sql_update = """
            UPDATE user_topic_scores 
            SET score = GREATEST(0, LEAST(1000, score + %s)) 
            WHERE user_id = %s AND topic = %s
            """
            cursor.execute(sql_update, (score_change, user_id, topic))

            sql_select = "SELECT score FROM user_topic_scores WHERE user_id = %s AND topic = %s"
            cursor.execute(sql_select, (user_id, topic))
            new_score = cursor.fetchone()['score']
            
        conn.commit()
        return new_score
    finally:
        conn.close()

def get_all_topic_scores(user_id: int) -> dict:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT topic, score FROM user_topic_scores WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()
            return {row['topic']: row['score'] for row in results}
    finally:
        conn.close()

def get_average_score(user_id: int) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT AVG(score) as avg_score FROM user_topic_scores WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()
            return int(result['avg_score']) if result and result['avg_score'] is not None else 500
    finally:
        conn.close()

# ✨ New: Score override function to forcefully set initial difficulty
def set_topic_score(user_id: int, topic: str, score: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO user_topic_scores (user_id, topic, score) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE score = VALUES(score)
            """
            cursor.execute(sql, (user_id, topic, score))
        conn.commit()
    finally:
        conn.close()

# ================= Wrong Question System =================

def record_wrong_question_to_db(user_id: int, category: str, content: str, student_ans: str, correct_ans: str, root_cause: str, improvement: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO wrong_questions 
            (user_id, category, question_content, student_answer, correct_answer, root_cause, improvement) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (user_id, category, content, student_ans, correct_ans, root_cause, improvement))
        conn.commit()
    finally:
        conn.close()

def get_user_weaknesses(user_id: int) -> list:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT DISTINCT category FROM wrong_questions WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()
            return [row['category'] for row in results]
    finally:
        conn.close()

def get_wrong_questions_details(user_id: int) -> list:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT category, question_content, student_answer, correct_answer, root_cause, improvement
            FROM wrong_questions 
            WHERE user_id = %s 
            ORDER BY id DESC
            """
            cursor.execute(sql, (user_id,))
            return cursor.fetchall()
    finally:
        conn.close()

def get_wrong_questions_by_topic(user_id: int, topic: str, limit: int = 3) -> list:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT question_content, student_answer, correct_answer 
            FROM wrong_questions 
            WHERE user_id = %s AND category LIKE %s
            ORDER BY id DESC LIMIT %s
            """
            cursor.execute(sql, (user_id, f"%{topic}%", limit))
            return cursor.fetchall()
    finally:
        conn.close()

# ================= Teacher Side / Admin Management =================

def get_all_users_overview() -> list:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Combined query: get user ID, username, average score (default 500 if none), and total wrong question count
            sql = """
            SELECT 
                u.id, 
                u.username,
                IFNULL(CAST(AVG(uts.score) AS SIGNED), 500) as avg_score,
                (SELECT COUNT(*) FROM wrong_questions wq WHERE wq.user_id = u.id) as wrong_count
            FROM users u
            LEFT JOIN user_topic_scores uts ON u.id = uts.user_id
            GROUP BY u.id, u.username
            ORDER BY avg_score DESC
            """
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Database module ready.")