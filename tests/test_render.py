import json,pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class RenderRegression(unittest.TestCase):
 def test_vertical_multisegment_keeps_exact_fps(self):
  with tempfile.TemporaryDirectory(prefix='ai-video-render-') as tmp:
   r=pathlib.Path(tmp)
   (r/'timeline.json').write_text(json.dumps({'duration':34/30,'fps':30}))
   (r/'index.html').write_text('<body style="margin:0;background:#123456"><script>window.ready=Promise.resolve();window.seek=t=>{document.body.style.background=t<.5?"#123456":"#50c090"};</script>')
   p=subprocess.run(['node',str(ROOT/'skill/ai-practical-video/scripts/render.mjs'),'--dir',str(r),'--video','--h','192','--workers','2'],capture_output=True,text=True)
   self.assertEqual(p.returncode,0,p.stderr)
   meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(r/'out/visual_192.mp4')]))['streams'][0]
   self.assertEqual((meta['width'],meta['height']),(108,192))
   self.assertEqual(meta['avg_frame_rate'],'30/1')
   self.assertEqual(int(meta['nb_frames']),34)
if __name__=='__main__':unittest.main()
