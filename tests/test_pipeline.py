import copy,datetime,json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'skill/ai-practical-video/scripts'))
from pipeline import init,write,read,rank,seal,reconcile,fail,lock,inside
AT='2026-10-21T12:00:00+08:00'
def candidate():
 return {'id':'a','title':'a','tool':'tool','feature':'feature','scenario':'scenario','event_at':'2026-10-20T10:00:00+08:00','sources':[{'kind':'official','url':'https://example.com/update','verified':True,'origin_id':'release-a'}],'business_use':'office','feature_verified':True,'demo_feasible':True,'scores':{'fit':4,'reproducibility':5,'service_demand':3}}
class Research(unittest.TestCase):
 def test_recent_is_not_automatically_hot(self):self.assertEqual(rank([candidate()],[],AT)['selected']['classification'],'近期更新')
 def test_old_story_reposted(self):
  c=candidate();c['event_at']='2026-08-01T00:00:00+08:00';c['sources'][0]['published_at']=AT
  self.assertEqual(rank([c],[],AT)['selected']['classification'],'常青选题')
 def test_reprints_are_one_origin(self):
  c=candidate();c['sources']*=4;self.assertEqual(rank([c],[],AT)['selected']['independent_origins'],1)
 def test_cumulative_count_not_trend(self):
  c=candidate();c['heat_signals']=[{'metric':'stars','value':358,'url':'https://example.com','observed_at':AT,'verified':True}]
  self.assertEqual(rank([c],[],AT)['selected']['classification'],'近期更新')
 def test_evidenced_heat(self):
  c=candidate();c['heat_signals']=[{'metric':'stars_added','value':100,'url':'https://example.com','observed_at':AT,'verified':True,'window':'24h'}]
  self.assertEqual(rank([c],[],AT)['selected']['classification'],'有热度证据')
 def test_missing_access_rejected(self):
  c=candidate();c['demo_feasible']=False;self.assertIsNone(rank([c],[],AT)['selected'])
 def test_duplicate_and_meaningful_update(self):
  c=candidate();h=[{'key':'tool|feature|scenario','completed_at':'2026-10-01T00:00:00+08:00'}]
  self.assertIsNone(rank([c],h,AT)['selected']);c.update(material_change='new input type verified',change_source='https://example.com/release');self.assertIsNotNone(rank([c],h,AT)['selected'])
 def test_more_than_ten(self):
  with self.assertRaises(ValueError):rank([candidate()]*11,[],AT)
 def test_future_timestamp(self):
  c=candidate();c['event_at']='2027-01-01T00:00:00+08:00';self.assertIsNone(rank([c],[],AT)['selected'])
 def test_date_only_official_update_is_recent_without_fake_timestamp(self):
  c=candidate();c.update(event_at=None,event_date='2026-10-16');s=rank([c],[],AT)['selected']
  self.assertEqual(s['classification'],'近期更新');self.assertIsNone(s['event_at'])
  self.assertEqual(s['event_time_bounds'],{'precision':'date','earliest':'2026-10-15T18:00:00+08:00','latest':'2026-10-17T22:00:00+08:00','timezone_known':False})
 def test_date_only_old_repost_stays_evergreen(self):
  c=candidate();c.update(event_at=None,event_date='2026-10-01');c['sources'][0]['published_at']=AT
  self.assertEqual(rank([c],[],AT)['selected']['classification'],'常青选题')
 def test_date_only_seven_day_boundary_gets_no_freshness(self):
  c=candidate();c.update(event_at=None,event_date='2026-10-14');s=rank([c],[],AT)['selected']
  self.assertEqual(s['classification'],'常青选题');self.assertEqual(s['score'],63)
 def test_date_only_72_hour_boundary_gets_only_seven_day_points(self):
  c=candidate();c.update(event_at=None,event_date='2026-10-18');self.assertEqual(rank([c],[],AT)['selected']['score'],72)
  c['event_date']='2026-10-19';self.assertEqual(rank([c],[],AT)['selected']['score'],78)
 def test_date_only_future_rejected_and_current_boundary_not_promoted(self):
  c=candidate();c.update(event_at=None,event_date='2026-10-24');self.assertIsNone(rank([c],[],AT)['selected'])
  c['event_date']='2026-10-21';s=rank([c],[],AT)['selected'];self.assertEqual(s['classification'],'常青选题');self.assertEqual(s['score'],63)
 def test_exact_event_time_takes_precedence_over_date(self):
  c=candidate();c.update(event_at='2026-08-01T00:00:00+08:00',event_date='2026-10-19')
  self.assertEqual(rank([c],[],AT)['selected']['classification'],'常青选题')
class Recovery(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=init(self.tmp.name,'test');
  for s in ['research','demo','script','voice','timeline','preview','final','qa','package']:
   f=s+'.txt';(self.r/f).write_text(s);seal(self.r,s,[],[f])
 def tearDown(self):self.tmp.cleanup()
 def test_script_change_invalidates_descendants(self):
  (self.r/'script.txt').write_text('revised');m=reconcile(self.r)
  self.assertEqual(m['stages']['demo']['state'],'complete');self.assertTrue(all(m['stages'][s]['state']=='stale' for s in ['script','voice','timeline','preview','final','qa','package']))
 def test_capture_loss_keeps_research(self):
  (self.r/'demo.txt').unlink();m=reconcile(self.r);self.assertEqual(m['stages']['research']['state'],'complete');self.assertEqual(m['stages']['demo']['state'],'stale')
 def test_render_interruption_keeps_timeline(self):
  (self.r/'final.txt').unlink();m=reconcile(self.r);self.assertEqual(m['stages']['timeline']['state'],'complete');self.assertEqual(m['stages']['final']['state'],'stale')
 def test_technical_retry_budget(self):
  for i in range(3):fail(self.r,'final','encoder interruption')
  self.assertFalse(read(self.r/'manifest.json')['stages']['final']['repair_allowed'])
 def test_demo_only_one_repair(self):
  fail(self.r,'demo','capture');fail(self.r,'demo','capture');self.assertFalse(read(self.r/'manifest.json')['stages']['demo']['repair_allowed'])
 def test_wait_does_not_spend_repair(self):
  fail(self.r,'voice','needs cost approval',waiting=True);m=read(self.r/'manifest.json');self.assertEqual(m['stages']['voice']['failures'],0);self.assertEqual(m['status'],'waiting')
 def test_login_wait_keeps_outputs(self):
  fail(self.r,'demo','login expired',waiting=True);self.assertTrue((self.r/'demo.txt').exists())
 def test_prerequisite_gate(self):
  (self.r/'script.txt').write_text('new')
  with self.assertRaises(ValueError):seal(self.r,'voice',[],['voice.txt'])
 def test_path_escape(self):
  with self.assertRaises(ValueError):inside(self.r,'../outside')
 def test_sequential_lock(self):
  with lock(self.tmp.name):
   with self.assertRaises(RuntimeError):
    with lock(self.tmp.name):pass
if __name__=='__main__':unittest.main(verbosity=2)
