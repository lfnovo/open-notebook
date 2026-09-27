import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('ranking',Path(__file__).parents[1]/'overlay/open_notebook/modules/hybrid_search/ranking.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class RankingTests(unittest.TestCase):
 def test_all_characters_covered_and_offsets_exact(self):
  for text in ['a','Türkçe İSTANBUL ı ğ ş 🚀\n'*300,'```mermaid\nA-->B\n```\n'*200,'x'*5000,'\n \t'*3000]:
   chunks=list(r.passages(text));covered=set()
   for c in chunks:
    self.assertEqual(c['content'],text[c['start']:c['end']]);self.assertLessEqual(len(c['content'].encode()),1600)
    covered.update(range(c['start'],c['end']))
   self.assertEqual(len(covered),len(text))
 def test_identifier_is_not_a_prefix_match(self):
  self.assertTrue(r.exact_match('AB-123 nedir?',{'content':'AB-123 cihazı','title':''}))
  self.assertFalse(r.exact_match('AB-123 nedir?',{'content':'AB-1234 cihazı','title':''}))
 def test_quoted_phrase_must_be_present(self):
  self.assertTrue(r.exact_match('"look-ahead bias"',{'content':'A look-ahead bias error','title':''}))
  self.assertFalse(r.exact_match('"look-ahead bias"',{'content':'look ahead','title':''}))
 def test_turkish_case_and_punctuation(self):
  self.assertIn('ısparta',r.query_terms('ISPARTA'))
  self.assertIn('istanbul',r.query_terms('İSTANBUL'))
  self.assertIn('ab-123',r.query_terms('AB-123 nedir?'))
 def test_rank_not_raw_score(self):
  results=r.fuse({'bm25_tr':[{'id':'a','score':9000},{'id':'b','score':8000}], 'vector':[{'id':'b','score':.1}]})
  self.assertEqual(results[0]['id'],'b')
 def test_duplicate_in_one_channel_no_extra_vote(self):
  self.assertEqual(r.fuse({'vector':[{'id':'a'},{'id':'a'}]})[0]['rrf_score'],1/61)
 def test_group_retains_distinct_origins(self):
  rows=[{'id':'p'+str(i),'doc_id':doc,'parent_id':doc,'title':doc,'content':'same','start':0,'end':4,'sha256':'same','rrf_score':.1,'channels':['vector']} for i,doc in enumerate(['note:a','note:b','note:a'])]
  results=r.group_results(rows,10)
  self.assertEqual(len(results),2);self.assertEqual(len(results[0]['matches']),1)
 def test_query_terms_bounded_and_unique(self):
  self.assertEqual(r.query_terms('code code'),['code'])
  self.assertLessEqual(len(r.query_terms(' '.join('token'+str(i) for i in range(100)))),16)
 def test_empty_text_no_fake_passage(self):
  self.assertEqual(list(r.passages('')),[])

if __name__=='__main__':unittest.main()
