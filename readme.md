🤖 AI Adaptive Tutor - Comprehensive Technical Documentation
📌 1. Core Mechanisms & Algorithm Deep Dive
This project is an AI-powered adaptive learning system (AI Tutor) designed to dynamically assess a student's knowledge level, generate personalized practice questions, and provide targeted feedback. To eliminate AI hallucinations and ensure high-quality educational content, the system deeply integrates Large Language Models (LLMs) with external real-world knowledge retrieval.

1.1 Dynamic Adaptive Questioning & Assessment System
The system uses a 1000-point scale and establishes a refined dynamic capability model. First-time users can choose their initial difficulty ranging from "Absolute Beginner" (100 points) to "Challenge Limit" (800 points). The system dynamically matches question difficulty based on the real-time score for that specific topic:

Basic Introduction (Score < 300): The system generates basic level 1-2 questions.

Advanced Improvement (Score 300-699): The system generates intermediate level 3-4 questions.

Mastery Challenge (Score ≥ 700): The system generates high-difficulty level 5 challenge questions.

1.2 Original "Flexible Elo" Dynamic Scoring & Streak Mechanism
The system adopts an Elo-inspired scoring system that also considers student psychology:

Base Scoring: The LLM only evaluates the answer performance to provide an absolute base score change between 10 and 20 points.

Difficulty & Streak Bonuses: Correct answers include a difficulty multiplier bonus (+5 × difficulty_level), while wrong answers penalize lower-difficulty questions more heavily. A streak of 3 or more consecutive correct answers triggers a combo bonus (up to +30 points).

Incorrect Streak Protection: Missing 3 or more consecutive questions triggers a gentle penalty (capped at -15 points) to avoid discouraging struggling students.

Dynamic Elo Resistance: As scores increase, it becomes harder to gain points (Multiplier = 1.0 - (current_score / 2000.0)); for lower scores, the penalty is reduced to protect confidence (Multiplier = 0.5 + (current_score / 2000.0)).

1.3 Phased Learning Diagnosis & Wrong Question Notebook
5-Question Phase Review: A comprehensive review is triggered every 5 questions, categorizing the student into a Struggling, Average, or Top student learning path.

Customized Study Packs: Struggling students receive a 1-minute video script explanation and laddered practice steps; Average students receive core concept clarifications and methodology summaries; Top students receive high-level extension challenges and cross-scenario application cases.

Knowledge Graph Visualization: The phase review generates Mermaid.js syntax code to visualize the diagnostic results as an intuitive knowledge graph.

Smart Wrong Question Notebook: Records student answers and correct answers, utilizing the LLM to generate deep "root-cause analysis" and actionable "improvement suggestions."

🛠️ 2. Tech Stack & Database Architecture Design
2.1 Tech Stack Overview
Backend Core: Built with the FastAPI framework and served using Uvicorn.

Database: Uses MySQL, interacting with data via the pymysql library.

LLM & AI: Integrates the deepseek-chat model, utilizing Pydantic to enforce strict JSON outputs. Integrates exa_py for real-time web retrieval.

Security & Frontend: Employs bcrypt for password hashing. The frontend is a Single Page HTML Application (SPA) styled with Tailwind CSS, relying on MathJax (for math formulas) and Mermaid.js (for knowledge graphs).

2.2 Database Architecture (Database Schema)
The underlying system relies on three core tables to support the adaptive logic:

users Table: Stores user ID, username, and the bcrypt password hash.

user_topic_scores Table: Tracks each user's specific score on independent topics. The default starting score is 500, with a hard floor of 0 and a ceiling of 1000.

wrong_questions Table: Logs the user ID, topic category, original question content, student's answer, correct answer, and the LLM-generated root cause and improvement suggestions.

🚀 3. Complete Backend Deployment Guide
Step 1: Environment & Dependency Preparation
Ensure Python 3.8+ and MySQL services are installed locally. Run the following command in the project root directory to install dependencies:

Bash
pip install fastapi uvicorn pymysql bcrypt openai exa_py pydantic
Step 2: Database Initialization & Configuration
Create a database named ai_tutor_db in MySQL.

Open database.py and modify the host, user, and password in DB_CONFIG to match your actual database credentials.

Execute the SQL statements provided in readme.md to set up the tables. You can run the test_db.py script to verify if the connection is successful.

Step 3: Environment Variables Configuration
The system strongly relies on external APIs. Configure the following environment variables (or replace the default values in llm_service.py):

DEEPSEEK_API_KEY: LLM API key.

EXA_API_KEY: Exa search engine API key.

Step 4: Starting the Service
Run the following command in the terminal to start the backend:

Bash
python main.py
# Or
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
💻 4. Frontend Interaction Flow & Core JavaScript Logic
The frontend page new.html is written in vanilla JS without frameworks, achieving a smooth Single Page Application (SPA) experience through precise state management and DOM manipulation.

4.1 Authentication & Capability Probe Determination
State Isolation: After a successful login, the frontend calls the /api/stats endpoint to load the user's historical topic scores, saving them in the userTopicScores dictionary.

Smart Difficulty Hiding: The checkDifficultyRequirement() function evaluates whether the user has historical scores for the currently selected topic. If records exist, the four "assess current level" difficulty buttons are intelligently hidden; if it's the user's first time encountering the field, they are forced to select an initial level to anchor the difficulty of the first question.

4.2 Topic Auto-Detection Debounce
When a user inputs a custom subject, handleCustomSubjectInput() triggers an 800-millisecond setTimeout debounce mechanism. This prevents the system from spamming the backend LLM API while the user is typing. Only after the input pauses will it request the /api/topics endpoint to automatically generate core topics for that specific subject.

4.3 Dynamic Rendering & Wrong Question Diagnosis Flow
Rich Text Support: When rendering questions and the wrong question notebook, the frontend uniformly uses marked.parse() to render Markdown content and calls MathJax.typesetPromise() to safely render math and chemistry formulas.

State Machine Control: During the answering phase, boolean variables isAnswering and isFetching lock the button states to prevent duplicate submissions caused by multi-clicks due to network latency.

Dynamic Graph Mounting: When the user completes 5 consecutive questions, triggering the review, renderReviewModal() mounts the pure Mermaid code sent by the backend into the DOM and calls mermaid.run() to instantly draw the knowledge diagnosis tree.

🧠 5. Exa Retrieval-Augmented Generation (RAG) & LLM Prompt Core Logic
The core intelligence of the system is centralized in llm_service.py.

5.1 Exa External Knowledge Retrieval Logic (RAG)
Generating Subject Topics: When a user inputs a custom subject, the system sends {subject} course outline core topics chapter list to Exa, automatically fetching the first 600 characters of the top two articles as a reference.

Generating Question Background: During question generation, it sends {subject} {topic} core knowledge classic questions to fetch the first 1000 characters of the top 2 results as a "reference material library" to feed the LLM and prevent hallucinations.

5.2 Core Prompt Design
Adaptive Question Prompt: Dynamically blends the capability tone (forcing a 1-5 difficulty based on score) and wrong question review (extracting historical incorrect questions on that topic for targeted correction), utilizing a Pydantic model to constrain the output fields.

Dynamic Scoring Prompt: Abandons hardcoding; the LLM only needs to provide a base score change of 10-20 points and output a root_cause and improvement for display in the wrong question notebook.

Phased Review Super Prompt: Inputs recent wrong questions and the average score grading, instructing the LLM to output pure Mermaid syntax code, and dynamically populates customized study pack content based on the student's learning path.

📈 6. Advanced: Exa RAG Performance Tuning Guide
The current RAG strategy has achieved basic factual anchoring, but to reach commercial-grade quality in the vertical education sector, the following fine-tuning of the Exa retrieval in llm_service.py is recommended:

Refactoring the Search Query (Prompt for Search):
The current search queries are somewhat generic, such as f"{subject} {topic} core knowledge classic questions".

Tuning Suggestion: Dynamically alter the search queries based on difficulty. For instance, for high-difficulty questions, changing the query to f"{subject} {topic} common misconceptions hard exam questions" makes it easier to capture "error traps," thereby generating high-quality challenge questions.

Optimizing Text Chunking Strategy:
The current code uses a hard truncation strategy: result.text[:1000]. This easily leads to truncating crucial knowledge located in the latter half of the text.

Tuning Suggestion: Enable the Exa API's Highlights feature, or add use_autoprompt=True to the Exa query parameters. This lets Exa internally optimize the search intent and fetch concentrated essential snippets instead of mechanically cutting off after the first 1000 characters.

Introducing Timeliness Control:
Certain subjects (like library function updates in computer science) are highly time-sensitive.

Tuning Suggestion: Add a time filter parameter to exa_client.search_and_contents (e.g., only retrieve content from the past 3 years) to prevent the LLM from generating incorrect questions based on outdated API documentation or obsolete theories.