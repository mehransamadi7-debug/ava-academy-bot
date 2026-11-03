import asyncio
import os
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, patch
import bot

def obj(**kw): return NS(**kw)
class BotTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.old=bot.STORE; bot.STORE=bot.Store(os.path.join(self.tmp.name,'state.sqlite'))
  bot.user_sessions.clear(); self.user=obj(id=42,first_name='Test',last_name='User',username='tester')
  self.bot=obj(send_message=AsyncMock(return_value=obj(message_id=200)))
  self.ctx=obj(bot=self.bot)
 def tearDown(self): bot.STORE=self.old; bot.user_sessions.clear(); self.tmp.cleanup()
 def cb(self,data,mid=10):
  q=obj(data=data,from_user=self.user,message=obj(chat_id=42,message_id=mid),answer=AsyncMock(),edit_message_text=AsyncMock(),edit_message_reply_markup=AsyncMock())
  return obj(callback_query=q),q
 def test_start_and_full_quiz_persist_duplicate_rejected_and_skip_report(self):
  update=obj(effective_user=self.user,message=obj(reply_text=AsyncMock()))
  asyncio.run(bot.start(update,self.ctx)); self.assertEqual(bot.STORE.get(42)['state'],'choosing_intent')
  u,q=self.cb('intent:curious'); asyncio.run(bot.callback_handler(u,self.ctx)); self.assertEqual(bot.STORE.get(42)['intent'],'curious'); self.assertEqual(bot.STORE.get(42)['state'],'choosing_language')
  u,q=self.cb('lang:en'); asyncio.run(bot.callback_handler(u,self.ctx)); self.assertEqual(bot.STORE.get(42)['state'],'quiz')
  first=bot.user_sessions[42]['current_msg_id']
  u,q=self.cb('ans:0:1',first); asyncio.run(bot.callback_handler(u,self.ctx)); self.assertEqual(bot.STORE.get(42)['score'],1)
  asyncio.run(bot.callback_handler(u,self.ctx)); self.assertEqual(bot.STORE.get(42)['score'],1); q.answer.assert_awaited()
  for i in range(1,10):
   msgid=bot.user_sessions[42]['current_msg_id']; answer=bot.QUESTIONS['en'][i][2]
   u,q=self.cb(f'ans:{i}:{answer}',msgid); asyncio.run(bot.callback_handler(u,self.ctx))
  self.assertEqual(bot.STORE.get(42)['state'],'awaiting_goal'); self.assertEqual(bot.STORE.get(42)['score'],10)
  u,q=self.cb('goal_curious'); asyncio.run(bot.callback_handler(u,self.ctx)); self.assertEqual(bot.STORE.get(42)['state'],'awaiting_contact')
  self.assertTrue(any('برآورد مقدماتی' in c.kwargs.get('text','') for c in self.bot.send_message.await_args_list))
  u,q=self.cb('contact_skip'); asyncio.run(bot.callback_handler(u,self.ctx)); saved=bot.STORE.get(42)
  self.assertEqual(saved['state'],'completed'); self.assertFalse(saved['consented_contact'])
  self.assertTrue(any('نه گواهی CEFR' in c.kwargs.get('text','') for c in self.bot.send_message.await_args_list))
  stats=bot.STORE.summary(); self.assertEqual((stats['users'],stats['completed'],stats['consented_contacts']),(1,1,0))
  self.assertEqual((stats['bot_start'],stats['intent_selected'],stats['quiz_started'],stats['quiz_completed'],stats['result_shown'],stats['contact_prompt_shown'],stats['contact_declined']),(1,1,1,1,1,1,1))
 def test_help_path_and_legacy_database_migration(self):
  # Simulate a DB created by the previous version (users table only).
  legacy=os.path.join(self.tmp.name,'legacy.sqlite')
  import sqlite3
  with sqlite3.connect(legacy) as db:
   db.execute("CREATE TABLE users (user_id INTEGER PRIMARY KEY, session_json TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
   db.execute("INSERT INTO users(user_id,session_json) VALUES (7, '{\"state\":\"completed\"}')")
  store=bot.Store(legacy); store.track('help_in_telegram')
  self.assertEqual(store.get(7)['state'],'completed'); self.assertEqual(store.summary()['help_in_telegram'],1)
  bot.STORE=store
  bot.user_sessions[42]={'state':'awaiting_contact','language':'en','score':4,'goal':'هدف'}; bot.STORE.put(42,bot.user_sessions[42])
  u,q=self.cb('contact_help'); asyncio.run(bot.callback_handler(u,self.ctx))
  self.assertEqual(bot.STORE.get(42)['state'],'completed'); self.assertEqual(bot.STORE.summary()['help_in_telegram'],2)
  self.assertFalse(bot.STORE.get(42).get('consented_contact',False))
  self.assertEqual(bot.STORE.summary()['consultation_menu_shown'],1)
  menu_call=self.bot.send_message.await_args_list[-1]
  keyboard=menu_call.kwargs['reply_markup'].inline_keyboard
  self.assertEqual([row[0].url for row in keyboard],[bot.CONSULTANT_WHATSAPP_URL,bot.CONSULTATION_URL,bot.WEBSITE_URL])
  self.assertEqual(bot.CONSULTANT_WHATSAPP_URL,'https://wa.me/989961665190')
  self.assertNotIn('https://t.me/',menu_call.kwargs['text'])
  self.assertNotIn('https://t.me/',' '.join(row[0].url for row in keyboard))
  self.assertIn('شخصاً ارسال کنید',menu_call.kwargs['text'])
  self.assertIn('خودکار منتقل نمی‌کند',menu_call.kwargs['text'])
  self.assertIn('تضمین‌شده‌ای وجود ندارد',menu_call.kwargs['text'])
  self.assertEqual(bot.STORE.summary()['contact_consent_given'],0)
  self.assertEqual(bot.STORE.summary()['phone_submitted'],0)

 def test_intent_selection_is_optional_path_enabled_and_report_counts(self):
  upd=obj(effective_user=self.user,message=obj(reply_text=AsyncMock()))
  asyncio.run(bot.start(upd,self.ctx))
  self.assertEqual(bot.STORE.get(42)['state'],'choosing_intent')
  # The intent prompt can be explicitly skipped; quiz remains accessible without tracking an intent.
  u,q=self.cb('intent:skip'); asyncio.run(bot.callback_handler(u,self.ctx))
  self.assertEqual(bot.STORE.get(42)['state'],'choosing_language')
  u,q=self.cb('lang:en'); asyncio.run(bot.callback_handler(u,self.ctx))
  self.assertEqual(bot.STORE.get(42)['state'],'quiz')
  self.assertNotIn('intent',bot.STORE.get(42))
  self.assertEqual(bot.STORE.summary()['intent_selected'],0)
  self.assertEqual(bot.STORE.summary()['quiz_started'],1)
  # An intent-free user still reaches the quiz and receives a result without sharing a phone.
  for i in range(10):
   sid=bot.user_sessions[42]['current_msg_id']; answer=bot.QUESTIONS['en'][i][2]
   u,q=self.cb(f'ans:{i}:{answer}',sid); asyncio.run(bot.callback_handler(u,self.ctx))
  self.assertEqual(bot.STORE.get(42)['state'],'awaiting_goal')
  u,q=self.cb('goal_curious'); asyncio.run(bot.callback_handler(u,self.ctx))
  u,q=self.cb('contact_skip'); asyncio.run(bot.callback_handler(u,self.ctx))
  stats=bot.STORE.summary()
  self.assertEqual((stats['bot_start'],stats['intent_selected'],stats['quiz_started'],stats['quiz_completed'],stats['result_shown'],stats['contact_prompt_shown'],stats['contact_declined']), (1,0,1,1,1,1,1))
  self.assertEqual(stats['consented_contacts'],0)

 def test_contact_requires_consent_and_admin_notice(self):
  bot.user_sessions[42]={'state':'awaiting_contact','language':'de','score':3,'goal':bot.GOALS['goal_exam']}; bot.STORE.put(42,bot.user_sessions[42])
  msg=obj(contact=obj(phone_number='+1234567',user_id=42),reply_text=AsyncMock())
  upd=obj(effective_user=self.user,message=msg)
  with patch.dict(os.environ,{'ADMIN_CHAT_ID':'900'}): asyncio.run(bot.contact_handler(upd,self.ctx))
  self.assertEqual(bot.STORE.get(42)['state'],'completed'); self.assertTrue(bot.STORE.get(42)['consented_contact'])
  self.assertEqual(self.bot.send_message.await_args.kwargs['chat_id'],900)
  self.assertEqual(bot.STORE.summary()['consented_contacts'],1)
 def test_reject_other_or_unverified_contact(self):
  bot.user_sessions[42]={'state':'awaiting_contact'}
  for uid in (99,None):
   msg=obj(contact=obj(phone_number='+000',user_id=uid),reply_text=AsyncMock()); upd=obj(effective_user=self.user,message=msg)
   asyncio.run(bot.contact_handler(upd,self.ctx)); self.assertEqual(bot.user_sessions[42]['state'],'awaiting_contact')
  self.bot.send_message.assert_not_awaited()
 def test_funnel_and_session_never_store_phone_or_message_text(self):
  phone='+989121234567'; private='متن خصوصی آزمایشی'
  bot.user_sessions[42]={'state':'awaiting_contact','language':'en','score':5,'goal':'سفر'}
  bot.STORE.put(42,bot.user_sessions[42]); msg=obj(contact=obj(phone_number=phone,user_id=42),reply_text=AsyncMock()); upd=obj(effective_user=self.user,message=msg)
  asyncio.run(bot.contact_handler(upd,self.ctx))
  import sqlite3
  with sqlite3.connect(bot.STORE.path) as db:
   cols=[r[1] for r in db.execute('PRAGMA table_info(funnel_events)')]
   events=[r[0] for r in db.execute('SELECT event FROM funnel_events')]
   raw=db.execute('SELECT session_json FROM users WHERE user_id=42').fetchone()[0]
  self.assertEqual(cols,['id','event','created_at']); self.assertNotIn(phone,raw); self.assertNotIn(private,raw)
  self.assertNotIn(phone,' '.join(events)); self.assertNotIn(private,' '.join(events))
  self.assertEqual(events,['contact_consent_given','phone_submitted'])
 def test_consultation_command_before_and_after_completion_is_private_guidance(self):
  expected_urls=[bot.CONSULTANT_WHATSAPP_URL,bot.CONSULTATION_URL,bot.WEBSITE_URL]
  self.assertEqual(bot.CONSULTANT_WHATSAPP_URL,'https://wa.me/989961665190')
  for state in ('choosing_intent','completed'):
   bot.user_sessions[42]={'state':state,'result_shown':state=='completed','consented_contact':False,'score':7}
   bot.STORE.put(42,bot.user_sessions[42])
   before=bot.STORE.summary().copy()
   message=obj(reply_text=AsyncMock())
   update=obj(effective_user=self.user,message=message)
   asyncio.run(bot.consultation_command(update,self.ctx))
   args=message.reply_text.await_args.kwargs
   self.assertEqual([row[0].url for row in args['reply_markup'].inline_keyboard],expected_urls)
   self.assertNotIn('https://t.me/',args['text'])
   self.assertNotIn('https://t.me/',' '.join(row[0].url for row in args['reply_markup'].inline_keyboard))
   self.assertIn('شخصاً ارسال کنید',args.args[0])
   self.assertIn('خودکار منتقل نمی‌کند',args['text'])
   after=bot.STORE.summary()
   self.assertEqual(bot.STORE.get(42),{'state':state,'result_shown':state=='completed','consented_contact':False,'score':7})
   self.assertEqual(after['completed'],before['completed'])
   self.assertEqual(after['quiz_started'],before['quiz_started'])
   self.assertEqual(after['quiz_completed'],before['quiz_completed'])
   self.assertEqual(after['contact_consent_given'],0)
   self.assertEqual(after['phone_submitted'],0)
   self.assertEqual(after['consultation_menu_shown'],before['consultation_menu_shown']+1)

 def test_stale_contact_callbacks_rejected_without_guidance_or_events(self):
  bot.user_sessions[42]={'state':'completed','consented_contact':False}
  bot.STORE.put(42,bot.user_sessions[42])
  for action in ('contact_help','contact_skip'):
   u,q=self.cb(action); asyncio.run(bot.callback_handler(u,self.ctx))
   q.answer.assert_awaited_with('این مرحله فعال نیست.',show_alert=True)
  self.assertEqual(bot.STORE.summary()['help_in_telegram'],0)
  self.assertEqual(bot.STORE.summary()['contact_declined'],0)
  self.assertEqual(bot.STORE.summary()['consultation_menu_shown'],0)

 def test_missing_token_error_is_generic_and_contains_no_secret(self):
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaises(RuntimeError) as caught: bot.main()
  self.assertEqual(str(caught.exception),'BOT_TOKEN environment variable is required')
  self.assertNotIn('secret',str(caught.exception).lower())
 def test_store_replaces_atomically_and_report_bounds(self):
  store=bot.Store(os.path.join(self.tmp.name,'other.sqlite')); store.put(8,{'state':'one'}); store.put(8,{'state':'two'}); self.assertEqual(store.get(8),{'state':'two'})
  self.assertIn('100٪',bot.generate_attractive_report('<&','en',10,'goal'))
  self.assertIn('0٪',bot.generate_attractive_report('x','en',0,'g'))
if __name__=='__main__': unittest.main()
