"""Make result reports self contained without changing frozen analyses."""
from pathlib import Path
import datetime, hashlib, json

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protocol=HERE/'PROTOCOL.json'
for path in sorted(HERE.glob('T12-*/**/RESULT.txt')):
    record=path.parent/'RUN_RECORD.json'
    if not record.exists():continue
    text=path.read_text()
    marker='\nFull frozen protocol and run record\n'
    if marker in text:text=text.split(marker)[0].rstrip()+'\n'
    text=text.replace('Length and completion matched analyses retained lower rewrite flag rates in',
      'Restricting analyses to complete texts of 100 to 128 words retained lower rewrite flag rates in')
    before=sha(path)
    text+=marker+'\n'+protocol.read_text()+'\n'+record.read_text()
    provenance=path.parent/'REUSED_DETECTOR_PROVENANCE.json'
    if not provenance.exists() and path.parent.parent.name=='T12-B':
        provenance=path.parent.parent/'REUSED_DETECTOR_PROVENANCE.json'
    if provenance.exists():text+='\nReused historical detector provenance\n\n'+provenance.read_text()
    path.write_text(text)
    with (HERE/'REPORT_REVISIONS.jsonl').open('a') as f:
        f.write(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'file':str(path),'before_sha256':before,'after_sha256':sha(path),
          'protocol_sha256':sha(protocol),'script_sha256':sha(Path(__file__)),
          'change':'Clarified common word length band without asserting exact length matching. Embedded unchanged frozen protocol and run record. No analysis code, values, or thresholds changed.'})+'\n')
    print(path)
