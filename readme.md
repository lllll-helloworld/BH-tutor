# 🤖 AI Adaptive Tutor

**AI Adaptive Tutor** is an intelligent, dynamic educational platform designed to provide personalized learning experiences. Powered by Large Language Models (LLMs) and real-time search retrieval, the system dynamically generates questions, evaluates student answers, and adjusts difficulty based on individual performance using a sophisticated Elo-style scoring system.

## ✨ Core Features

* **Adaptive Learning Engine**: Dynamically adjusts question difficulty (Levels 1-5) based on the user's real-time score and historical performance.
* **LLM-Powered Generation & Evaluation**: Utilizes DeepSeek (via OpenAI API compatibility) to generate highly relevant questions and provide detailed root-cause analysis for incorrect answers.
* **Real-time Knowledge Retrieval**: Integrates with the **Exa API** to pull up-to-date, real-world context for question generation, reducing AI hallucinations.
* **Streak & Motivation System**: Rewards consecutive correct answers with combo multipliers and provides gentle encouragement for consecutive mistakes to protect student confidence.
* **Phase Reviews & Knowledge Graphs**: After every 5 questions, the system generates a personalized review, including remediation paths (tailored to Struggling, Average, or Top students) and renders visual knowledge maps using **Mermaid.js**.
* **Wrong Question Notebook**: Automatically tracks mistakes, categorizing them by topic, root cause, and improvement strategies for easy review.


---

## 🛠️ Tech Stack

**Backend**
* **Framework**: FastAPI (Python)
* **Database**: MySQL (PyMySQL)
* **Security**: bcrypt (Password hashing)
* **AI/LLM integration**: `openai` SDK (configured for DeepSeek), `exa_py` (Exa Search API)
* **Data Validation**: Pydantic

**Frontend**
* **Core**: HTML5, Vanilla JavaScript
* **Styling**: TailwindCSS
* **Rendering**: Marked.js (Markdown), MathJax (Mathematical formulas), Mermaid.js (Diagrams/Graphs)

---

## 🚀 Installation & Setup

### 1. Prerequisites
* Python 3.8 or higher
* MySQL Server (running locally or remotely)
* DeepSeek API Key
* Exa API Key

### 2. Install Dependencies
Make sure you are in the project root directory, then install the required Python packages:
```bash
pip install fastapi uvicorn pymysql bcrypt openai exa_py pydantic
3. Database Configuration
Ensure your MySQL server is running.

Create a database named ai_tutor_db.

Update your database credentials in database.py:

Python
DB_CONFIG = {
    'host': '127.0.0.1',      
    'user': 'root',           
    'password': 'your_secure_password', 
    'database': 'ai_tutor_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor 
}
Database Initialization (SQL Schema): Run the following SQL commands in your MySQL environment to set up the necessary tables for the application.

SQL
CREATE DATABASE IF NOT EXISTS ai_tutor_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_tutor_db;

-- Table for storing user credentials
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);

-- Table for tracking dynamic Elo scores per knowledge point
CREATE TABLE IF NOT EXISTS user_topic_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    topic VARCHAR(255) NOT NULL,
    score INT DEFAULT 500,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_topic (user_id, topic)
);

-- Table for logging incorrect answers and LLM feedback
CREATE TABLE IF NOT EXISTS wrong_questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category VARCHAR(255) NOT NULL,
    question_content TEXT NOT NULL,
    student_answer TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    root_cause TEXT,
    improvement TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
4. Environment Variables
Set your API keys as environment variables. If not set, the system will fallback to the default keys provided in llm_service.py (Not recommended for production).

DEEPSEEK_API_KEY

EXA_API_KEY

5. Run the Application
Start the FastAPI server using Uvicorn:

Bash
python main.py
Or run Uvicorn directly:

Bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
🎮 Usage Guide
Accessing the Portals
Student Portal: Open http://localhost:8000/ in your browser. Students can register, select subjects/topics, assess their initial level, and start answering questions.

Teacher Dashboard: Open http://localhost:8000/teacher to view the student performance overview.

Included Utility Scripts
The project includes several built-in scripts for database and system management:


change_score.py: An internal admin tool to manually override a specific user's score for a specific knowledge point. Useful for testing difficulty adjustments.

clear_data.py: A nuclear option to truncate all tables (users, user_topic_scores, wrong_questions) and restore the database to factory settings. Use with extreme caution.

test_db.py: A simple script to verify your MySQL connection configuration.

test_streaks.py: A unit testing suite mapping out the streak mechanism (tests consecutive correct/incorrect answers and their respective score multipliers). Run with python -m unittest test_streaks.py.

📂 Project Structure
main.py: The FastAPI application entry point, routing, and HTTP endpoints.

llm_service.py: Contains the AdaptiveLearningSystem class, prompt engineering, Exa retrieval logic, Elo scoring math, and OpenAI API calls.

database.py: Handles all PyMySQL queries, schema interactions, and bcrypt authentication.

new.html: The interactive Single Page Application (SPA) frontend for students.

teacher.html: The monitoring dashboard for educators. (Note: Ensure this file is created in your directory as referenced by main.py).

🌐 API Endpoints Overview
Auth: POST /api/register, POST /api/login

Core Learning:

GET /api/topics (Auto-generates topics for a custom subject using LLM)

GET /api/question (Fetches an adaptive question based on user state)

POST /api/submit (Submits answer, calculates Elo, returns LLM feedback & phase reviews)

Analytics:

GET /api/stats (User's personal weakness distribution and wrong questions)

GET /api/admin/dashboard (Global student overview for teachers)