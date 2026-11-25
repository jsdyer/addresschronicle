import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh import parse_ocr,parse_labels,validate_config
class RefreshTests(unittest.TestCase):
 def xml(self,text):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);p=Path(t.name)/'x.xml';p.write_text(text);return p
 def test_blank_pages_preserve_reader_index_and_source_leaf(self):
  pages=['<OBJECT usemap="x_0001.djvu"><HIDDENTEXT/></OBJECT>']
  for n in range(2,7):pages.append(f'<OBJECT usemap="x_{n:04d}.djvu"><LINE><WORD>520</WORD><WORD>Granville</WORD></LINE></OBJECT>')
  out=parse_ocr(self.xml('<DjVuXML>'+''.join(pages)+'</DjVuXML>'));self.assertEqual(out[0]['leaf'],2);self.assertEqual(out[0]['reader_index'],1);self.assertEqual(out[0]['text'],'520 Granville')
 def test_unknown_page_identity_rejected(self):
  with self.assertRaises(ValueError):parse_ocr(self.xml('<root><OBJECT usemap="unknown"><LINE><WORD>x</WORD></LINE></OBJECT></root>'))
 def test_external_entities_rejected(self):
  with self.assertRaises(ValueError):parse_ocr(self.xml('<!DOCTYPE x SYSTEM "https://example.invalid/x"><root/>'))
 def test_printed_page_separate_from_leaf(self):
  x='<book><pageData><page leafNum="12"><pageNumber>4</pageNumber></page></pageData></book>';self.assertEqual(parse_labels(self.xml(x)),{12:'4'})
 def test_configuration_expands_without_fixed_count(self):
  d=json.loads((Path(__file__).resolve().parents[1]/'config/collections.json').read_text());d['volumes'].append({**d['volumes'][0],'id':'additional-real-item'});self.assertIs(validate_config(d),d)
 def test_duplicate_or_path_identifiers_rejected(self):
  d=json.loads((Path(__file__).resolve().parents[1]/'config/collections.json').read_text());d['volumes'][0]['id']='../../etc/passwd'
  with self.assertRaises(ValueError):validate_config(d)
