# test_streaks.py
import unittest
from unittest.mock import patch
from llm_service import evaluate_student_answer, AnswerPayload

class TestStreakSystem(unittest.TestCase):

    def setUp(self):
        
        import llm_service
        llm_service.user_streaks = {}
        llm_service.current_question_state = {}
        llm_service.user_total_answers = {}
        
        
        self.mock_db_score = 500
        self.user_id = 1

   
    def mock_get_topic_score(self, uid, topic):
        return self.mock_db_score

    def mock_update_topic_score(self, uid, topic, change):
        
        self.mock_db_score += change
        return self.mock_db_score

   
    @patch('llm_service.get_topic_score')
    @patch('llm_service.update_topic_score')
    @patch('llm_service.record_wrong_question_to_db')
    @patch('llm_service.global_system.evaluate_answer_by_llm')
    def test_correct_streak(self, mock_llm, mock_record, mock_update, mock_get_score):
        mock_get_score.side_effect = self.mock_get_topic_score
        mock_update.side_effect = self.mock_update_topic_score
        
       
        mock_llm.return_value = {
            "score_change": 20, 
            "root_cause": "理解透彻",
            "improvement": "继续保持"
        }

        import llm_service
        print("\n--- 开始测试【连对机制】---")
        
        for i in range(1, 5):
            llm_service.current_question_state[self.user_id] = {
                "correct_answer": "A", 
                "category": "测试考点", 
                "content": "测试题目",
                "difficulty": 2
            }
            
            payload = AnswerPayload(user_id=self.user_id, answer="A")
            result = evaluate_student_answer(payload)
            
            print(f"第 {i} 次答对: 消息 -> '{result.get('streak_msg', '')}' | 当前总分 -> {result['current_score']}")
            
            if i == 1 or i == 2:
                self.assertEqual(result.get('streak_msg'), "") 
            elif i == 3:
               
                self.assertIn("达成 3 连对，额外加成 5 分", result['streak_msg']) 
            elif i == 4:
                
                self.assertIn("达成 4 连对，额外加成 10 分", result['streak_msg'])

   
    @patch('llm_service.get_topic_score')
    @patch('llm_service.update_topic_score')
    @patch('llm_service.record_wrong_question_to_db')
    @patch('llm_service.global_system.evaluate_answer_by_llm')
    def test_wrong_streak(self, mock_llm, mock_record, mock_update, mock_get_score):
        mock_get_score.side_effect = self.mock_get_topic_score
        mock_update.side_effect = self.mock_update_topic_score
        
        mock_llm.return_value = {
            "score_change": -15, 
            "root_cause": "概念混淆",
            "improvement": "重看教材"
        }

        import llm_service
        print("\n--- 开始测试【连错机制】---")
        
        for i in range(1, 5):
            llm_service.current_question_state[self.user_id] = {
                "correct_answer": "A", 
                "category": "测试考点", 
                "content": "测试题目",
                "difficulty": 2
            }
            
            payload = AnswerPayload(user_id=self.user_id, answer="B")
            result = evaluate_student_answer(payload)
            
            print(f"第 {i} 次答错: 消息 -> '{result.get('streak_msg', '')}' | 当前总分 -> {result['current_score']}")
            
            if i == 1 or i == 2:
                self.assertEqual(result.get('streak_msg'), "")
            elif i == 3:
                self.assertIn("连续答错 3 题", result['streak_msg'])
            elif i == 4:
                self.assertIn("连续答错 4 题", result['streak_msg'])

if __name__ == '__main__':
    unittest.main(verbosity=0)