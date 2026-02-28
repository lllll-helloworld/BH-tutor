# llm_service.py
import os
import json
import re
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from openai import OpenAI
from exa_py import Exa  
from database import (
    get_user_info, record_wrong_question_to_db, 
    get_user_weaknesses, get_wrong_questions_by_topic, get_wrong_questions_details,
    get_topic_score, update_topic_score, get_average_score, set_topic_score
)

class AnswerPayload(BaseModel):
    user_id: int   
    answer: str  

class GeneratedQuestion(BaseModel):
    stage: str = Field(description="Stage name, must be one of: Basic Introduction / Advanced Improvement / Mastery Challenge")
    category: str = Field(description="Specific knowledge point name")
    difficulty: int = Field(description="Difficulty coefficient, must be an integer between 1 and 5")
    content: str = Field(description="Question description, supports Markdown")
    options: Dict[str, str] = Field(description="Options dictionary, e.g. {'A': 'Option1', 'B': 'Option2', 'C': 'Option3', 'D': 'Option4'}")
    correct_answer: str = Field(description="Letter of the correct option, e.g. 'A'")

class EvaluationFeedback(BaseModel):
    score_change: int = Field(description="Base score change, positive for addition, negative for deduction")
    root_cause: str = Field(description="Root cause of error or core point, limited to 50 characters")
    improvement: str = Field(description="Improvement suggestions or consolidation methods, limited to 50 characters")

class PhaseReviewContent(BaseModel):
    # Exclusive for struggling students
    video_script: str = Field(default="", description="1-minute easy-to-understand explanation script for knowledge point (for struggling students)")
    practices: List[str] = Field(default_factory=list, description="Array of laddered practice questions (for struggling students)")
    # Exclusive for average students
    core_concept_clarification: str = Field(default="", description="Clarification of easily confused core concepts (for average students)")
    methodology_summary: str = Field(default="", description="Summary of problem-solving routines and techniques (for average students)")
    # Exclusive for top students
    extension_q: str = Field(default="", description="High-level extension challenge question (for top students)")
    application_case: str = Field(default="", description="Cross-scenario application case (for top students)")

class PhaseReviewResult(BaseModel):
    gap: str = Field(description="One-sentence diagnosis of the student's potential core knowledge gap or ability bottleneck, limited to 30 characters")
    mermaid_graph: str = Field(description="Pure Mermaid syntax code, note that node text must be enclosed in double quotes (e.g., A[\"text\"]), absolutely no Markdown markers or ```mermaid modifiers")
    path_type: str = Field(description="Must be one of: 'Top Student', 'Average Student', or 'Struggling Student'")
    content: PhaseReviewContent

class TopicList(BaseModel):
    topics: List[str] = Field(description="5 core knowledge points/chapter names for this subject")

class AdaptiveLearningSystem:
    def __init__(self, api_key, base_url=None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = "deepseek-chat" 
        
        exa_api_key = os.getenv("EXA_API_KEY", "input your key here") 
        try:
            self.exa_client = Exa(exa_api_key)
        except Exception as e:
            print(f"⚠️ Exa client initialization failed, please check API KEY. Error message: {e}")
            self.exa_client = None

    def retrieve_background_knowledge(self, subject: str, topic: str = None) -> str:
        if not self.exa_client:
            return "(No valid Exa key configured, this question relies solely on model internal knowledge)"
            
        search_query = f"{subject} {topic if topic else ''} core knowledge classic questions"
        try:
            print(f"🔍 Retrieving via Exa: {search_query}")
            search_response = self.exa_client.search_and_contents(
                search_query,
                num_results=2, 
                text=True
            )
            
            context_pieces = []
            for result in search_response.results:
                context_pieces.append(f"Source: {result.title}\nContent Summary: {result.text[:1000]}")
                
            return "\n\n".join(context_pieces)
        except Exception as e:
            print(f"⚠️ Exa retrieval failed: {e}")
            return "(Due to network or quota issues, external knowledge could not be obtained; degraded to model internal knowledge)"

    def generate_topics_for_subject(self, subject: str) -> list:
        context = ""
        if self.exa_client:
            try:
                print(f"🔍 Retrieving outline for【{subject}】via Exa...")
                search_response = self.exa_client.search_and_contents(
                    f"{subject} course outline core topics chapter list",
                    num_results=2, 
                    text=True
                )
                context = "\n".join([f"Source: {r.title}\nContent: {r.text[:600]}" for r in search_response.results])
            except Exception as e:
                print(f"⚠️ Exa outline retrieval failed: {e}")
                context = "Failed to retrieve external materials, please rely on internal knowledge."
        
        prompt = f"""
        You are an education expert. Based on the following reference materials, extract the 5 most representative core knowledge points or chapter names for the subject【{subject}】(try to keep them short).
        Reference materials:
        {context}
        
        Please output strictly according to the following JSON Schema, do not output any other content:
        {json.dumps(TopicList.model_json_schema(), ensure_ascii=False)}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" },
                temperature=0.5
            )
            raw_content = response.choices[0].message.content
            match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            clean_content = match.group(0) if match else raw_content.strip()
            
            validated_data = TopicList.model_validate_json(clean_content)
            return validated_data.topics
        except Exception as e:
            print(f"Failed to parse knowledge points: {e}")
            return []

    def generate_question(self, user_id, subject, topic=None, initial_score=None):
        if initial_score is not None:
            score = initial_score
        else:
            score = get_topic_score(user_id, topic) if topic else get_average_score(user_id)
        
        # 👑 Optimized question generation prompt, strictly regulated difficulty levels
        if score < 300:
            level_desc = f"The student's current score is {score}/1000, at the 【Basic Introduction】 stage. Please generate a simple, single-core concept basic question. Difficulty coefficient must be set to (1 or 2)."
        elif score < 700:
            level_desc = f"The student's current score is {score}/1000, at the 【Advanced Improvement】 stage. Please generate an intermediate-level question with some depth and requiring comprehensive analysis. Difficulty coefficient must be set to (3 or 4)."
        else:
            level_desc = f"The student's current score is {score}/1000, at the 【Mastery Challenge】 stage. Please generate a high-difficulty, easy-to-mistake, multi-knowledge-point intersection challenge question. Difficulty coefficient must be set to (5)."
        
        wrong_q_prompt = ""
        if topic:
            wrong_qs = get_wrong_questions_by_topic(user_id, topic)
            if wrong_qs:
                details = "\n".join([
                    f"- Original question: {q['question_content']}\n  (Student incorrectly chose: {q['student_answer']}, correct answer: {q['correct_answer']})" 
                    for q in wrong_qs
                ])
                wrong_q_prompt = f"【Learning reference】The student has the following wrong question records in【{topic}】, please analyze their easily confused thinking pitfalls and create a new question to correct the error:\n{details}"
            else:
                wrong_q_prompt = f"【Learning reference】The student has no wrong question records in【{topic}】, please generate a regular test question that matches their current level."
        else:
            weaknesses = get_user_weaknesses(user_id)
            weak_prompt = f"[{'、'.join(weaknesses)}]" if weaknesses else "None yet"
            wrong_q_prompt = f"【Learning reference】The student's historical weak points include: {weak_prompt}. Please prioritize selecting one of these weak points for the question."

        ability_prompt = f"Current subject: {subject}.\nLevel assessment: {level_desc}"
        topic_instruction = f"Please strictly focus on the knowledge point【{topic}】to generate the question." if topic else "Please automatically select an appropriate knowledge point from this subject to generate the question."
        
        retrieved_context = self.retrieve_background_knowledge(subject, topic)
        
        prompt = f"""
        You are a senior mentor in the field of【{subject}】. Based on the following learning situation, independently decide on the question:
        {ability_prompt}
        {wrong_q_prompt}
        {topic_instruction}
        
        【Reference knowledge base】(Please prioritize referring to the following real materials retrieved from the web to construct the question stem and options, ensuring factual accuracy and avoiding hallucinations):
        {retrieved_context}
        
        Please output strictly according to the following JSON Schema, do not output any other content:
        {json.dumps(GeneratedQuestion.model_json_schema(), ensure_ascii=False)}
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" },
            temperature=0.7
        )
        
        raw_content = response.choices[0].message.content
        match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        clean_content = match.group(0) if match else raw_content.strip()
        
        try:
            validated_data = GeneratedQuestion.model_validate_json(clean_content)
            return validated_data.model_dump()
        except Exception as e:
            print(f"Failed to parse LLM generated question, validation error: {e}\nOriginal content: {raw_content}")
            return None

    def evaluate_answer_by_llm(self, subject, question_data, user_ans, is_correct):
        # 👑 Optimized scoring prompt: LLM only provides base performance score, abandoning hard-coded complex logic
        prompt = f"""
        You are a senior mentor in the field of【{subject}】. Please perform dynamic scoring and growth feedback based on the student's answer situation.
        
        【Question Information】
        Knowledge point: {question_data.get('category')}
        Difficulty: {question_data.get('difficulty')} (1-5)
        Question: {question_data.get('content')}
        Correct answer: {question_data.get('correct_answer')}
        
        【Student Answer】
        Student chose: {user_ans}
        Result: {'Correct' if is_correct else 'Incorrect'}
        
        【Scoring and Feedback Rules】
        1. Scoring: You only need to provide an absolute value of the **base score** between 10 and 20 (positive for correct answers e.g., 15, negative for incorrect e.g., -15). No need to consider difficulty and segment, the backend system will perform Elo and difficulty dynamic weighting.
        2. Feedback: Provide growth feedback, must point out the error root cause / core of the knowledge point, and give specific improvement methods.
        
        Please output strictly according to the following JSON Schema, do not output any other content:
        {json.dumps(EvaluationFeedback.model_json_schema(), ensure_ascii=False)}
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" },
            temperature=0.3
        )
        
        raw_content = response.choices[0].message.content
        match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        clean_content = match.group(0) if match else raw_content.strip()
        
        try:
            validated_data = EvaluationFeedback.model_validate_json(clean_content)
            return validated_data.model_dump()
        except Exception as e:
            return {
                "score_change": 15 if is_correct else -15, 
                "root_cause": "System judgment, please try again later", 
                "improvement": "Keep steady progress"
            }

    def generate_phase_review(self, user_id, subject, current_score):
        wrong_qs = get_wrong_questions_details(user_id)[:5] 
        if wrong_qs:
            wrong_context = "Recent wrong question review:\n" + "\n".join([f"- Knowledge point: {q['category']} | Original question: {q['question_content']}" for q in wrong_qs])
        else:
            wrong_context = "Recent performance is perfect, no wrong question records."

        if current_score < 300:
            path_type = "Struggling Student"
        elif current_score < 700:
            path_type = "Average Student"
        else:
            path_type = "Top Student"
        
        prompt = f"""
        You are a senior mentor in the field of【{subject}】. The student's current average score is {current_score}/1000 (classified as: {path_type} path).
        Please combine the student's recent learning situation to conduct a phased review and deduction, providing a knowledge graph and personalized learning path.
        Learning reference: {wrong_context}
        
        Please output strictly according to the following JSON Schema, do not output any additional text or code blocks:
        {json.dumps(PhaseReviewResult.model_json_schema(), ensure_ascii=False)}
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" },
            temperature=0.7
        )
        
        raw_content = response.choices[0].message.content
        match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        clean_content = match.group(0) if match else raw_content.strip()
        
        try:
            validated_data = PhaseReviewResult.model_validate_json(clean_content)
            return validated_data.model_dump()
        except Exception as e:
            return None

API_KEY = os.getenv("DEEPSEEK_API_KEY", "input your key here")
BASE_URL = BASE_URL = "https://api.deepseek.com/v1"

global_system = AdaptiveLearningSystem(api_key=API_KEY, base_url=BASE_URL)

current_question_state = {} 
user_streaks = {}  
user_total_answers = {}

def fetch_new_question(user_id: int, subject: str, topic: str = None, initial_score: int = None) -> dict:
    global current_question_state
    global user_total_answers
    
    question_data = global_system.generate_question(user_id, subject, topic, initial_score)
    if not question_data:
        return {"status": "error", "message": "LLM generated question format error, please retry"}
    
    question_data['subject'] = subject
    current_question_state[user_id] = question_data  
    
    topic_name = question_data.get("category", "Comprehensive")
    
    if initial_score is not None:
        set_topic_score(user_id, topic_name, initial_score)
        current_score = initial_score
    else:
        current_score = get_topic_score(user_id, topic_name)
    
    answered_count = user_total_answers.get(user_id, 0)
    current_q_num = (answered_count % 5) + 1
    
    return {
        "status": "success",
        "data": {
            "category": topic_name,
            "difficulty": question_data.get("difficulty", 2),
            "content": question_data.get("content", ""),
            "options": question_data.get("options", {}),
            "current_score": current_score,
            "current_q_num": current_q_num
        }
    }

def evaluate_student_answer(payload: AnswerPayload) -> dict:
    global current_question_state
    global user_streaks
    global user_total_answers
    
    user_id = payload.user_id
    
    if user_id not in current_question_state or not current_question_state[user_id]:
        return {"status": "error", "message": "Please get a question first!"}
        
    if user_id not in user_total_answers:
        user_total_answers[user_id] = 0
    user_total_answers[user_id] += 1
        
    question_state = current_question_state[user_id]
    user_ans = payload.answer.strip().upper()
    correct_ans = question_state.get("correct_answer")
    subject = question_state.get("subject", "General Subject")
    category = question_state.get("category", "Uncategorized")
    content = question_state.get("content", "")
    difficulty = question_state.get("difficulty", 2)
    
    is_correct = (user_ans == correct_ans)
    
    evaluation_result = global_system.evaluate_answer_by_llm(
        subject=subject,
        question_data=question_state, 
        user_ans=user_ans, 
        is_correct=is_correct
    )
    
    raw_score_change = evaluation_result.get("score_change", 0)
    root_cause = evaluation_result.get("root_cause", "None")
    improvement = evaluation_result.get("improvement", "None")
    
    try:
        base_score_change = int(raw_score_change)
    except ValueError:
        base_score_change = 15 if is_correct else -15
        
    # --- 1. Get current score and difficulty, apply difficulty weighting ---
    current_score = get_topic_score(user_id, category)

    if is_correct:
        # Correct: ensure base score is positive and add difficulty bonus
        base_score_change = abs(base_score_change) + (difficulty * 5)
    else:
        # Wrong: ensure base score is negative, lower difficulty (basic questions) deduct more
        base_score_change = -abs(base_score_change) - ((6 - difficulty) * 3)
        
    # --- 2. Gentle streak/miss mechanism (add upper limit) ---
    if user_id not in user_streaks:
        user_streaks[user_id] = 0
        
    if is_correct:
        user_streaks[user_id] = user_streaks[user_id] + 1 if user_streaks[user_id] > 0 else 1
    else:
        user_streaks[user_id] = user_streaks[user_id] - 1 if user_streaks[user_id] < 0 else -1
        
    streak = user_streaks[user_id]
    combo_bonus = 0
    streak_msg = ""
    
    if streak >= 3:
        # Correct streak bonus: increases by 5 each time, max extra 30 points
        combo_bonus = min(30, 5 * (streak - 2))
        streak_msg = f" 🔥 Achieved {streak} consecutive correct, extra bonus {combo_bonus} points!"
    elif streak <= -3:
        # Wrong streak penalty: decreases by 3 each time, max extra -15 points (avoid discouraging struggling students)
        combo_bonus = max(-15, -3 * (abs(streak) - 2))
        streak_msg = f" 🌧️ {abs(streak)} consecutive incorrect, don‘t be discouraged, read the analysis carefully!"
        
    raw_total_change = base_score_change + combo_bonus

    # --- 3. Dynamic Elo resistance mechanism ---
    if is_correct:
        # Higher score, harder to gain points
        multiplier = 1.0 - (current_score / 2000.0)
    else:
        # Lower score, less penalty, protect confidence
        multiplier = 0.5 + (current_score / 2000.0)

    expected_score_change = int(raw_total_change * multiplier)

    # Minimum guarantee: correct at least +1, wrong at least -1
    if is_correct and expected_score_change <= 0:
        expected_score_change = 1
    elif not is_correct and expected_score_change >= 0:
        expected_score_change = -1

    # Submit final score to database
    new_score = update_topic_score(user_id, category, expected_score_change)
    
    if not is_correct:
        record_wrong_question_to_db(user_id, category, content, user_ans, correct_ans, root_cause, improvement)
        
    review_data = None
    
    if user_total_answers[user_id] % 5 == 0:
        avg_score = get_average_score(user_id)
        review_data = global_system.generate_phase_review(user_id, subject, avg_score)
        if review_data:
            review_data['count'] = user_total_answers[user_id]  

    current_question_state[user_id] = {} 
    
    return {
        "status": "success",
        "is_correct": is_correct,
        "current_topic": category,
        "current_score": new_score, 
        "base_score_change": expected_score_change, 
        "streak_msg": streak_msg,
        "root_cause": root_cause,
        "improvement": improvement,
        "review_data": review_data
    }