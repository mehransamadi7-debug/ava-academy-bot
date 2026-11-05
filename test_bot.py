import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import bot


class RestoreTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        bot.user_sessions.clear()

    def test_questions(self):
        self.assertEqual(set(bot.QUESTIONS), {'en', 'de', 'fr', 'it'})
        for questions in bot.QUESTIONS.values():
            self.assertEqual(len(questions), 10)
            for q in questions:
                self.assertEqual(len(q['options']), 4)
                self.assertIn(q['answer'], range(4))

    def test_reports(self):
        for score in range(11):
            report = bot.generate_attractive_report('<user>', 'English', score, '<goal>')
            self.assertIn('&lt;user&gt;', report)
            self.assertIn('&lt;goal&gt;', report)
            self.assertIn(f'{score} از ۱۰', report)

    async def test_contact_sends_report_and_admin_lead(self):
        user = SimpleNamespace(id=123, first_name='Test', last_name=None, username=None)
        message = SimpleNamespace(contact=SimpleNamespace(phone_number='989000000000'), reply_text=AsyncMock())
        update = SimpleNamespace(effective_user=user, message=message)
        context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))
        bot.user_sessions[123] = dict(state='awaiting_contact', language='en', score=5, goal='test')
        with patch.dict(os.environ, {'ADMIN_CHAT_ID': '456'}):
            await bot.contact_handler(update, context)
        message.reply_text.assert_awaited_once()
        context.bot.send_message.assert_awaited_once()
        self.assertEqual(context.bot.send_message.call_args.kwargs['chat_id'], 456)
        self.assertIn('989000000000', context.bot.send_message.call_args.kwargs['text'])
        self.assertEqual(bot.user_sessions[123]['state'], 'completed')


if __name__ == '__main__':
    unittest.main()
