"""Clone the received B17 history; use an explicitly recorded CI candidate."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def main():
    source=ROOT/'exchange/b17'
    for line in (source/'SHA256SUMS').read_text().splitlines():
        expected,name=line.split(None,1)
        assert hashlib.sha256((source/name.strip()).read_bytes()).hexdigest()==expected
    dest=ROOT/'data/e13-b17-251880498'
    if dest.exists():raise ValueError('Preserve earlier input')
    dest.mkdir(parents=True)
    subprocess.run(['git','clone',str(source/'project.bundle'),str(dest/'repo')],check=True)
    shutil.copyfile(source/'candidate.Dockerfile',dest/'candidate.Dockerfile')
    lines=(source/'candidate.Dockerfile').read_text().splitlines()
    candidate=dest/'candidate-CI.Dockerfile'
    candidate.write_text('\n'.join([lines[0],'RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*',*[x for x in lines[1:] if not x.startswith('RUN sed ')]] )+'\n')
    request=json.loads((source/'request-e14.json').read_text())
    request['candidate']='/course/data/e13-b17-251880498/'+candidate.name
    (dest/'request-e14.json').write_text(json.dumps(request,indent=2)+'\n')
    evidence=ROOT/'work/ci-b17-candidate.json';evidence.parent.mkdir(exist_ok=True)
    evidence.write_text(json.dumps({'original_sha256':hashlib.sha256((source/'candidate.Dockerfile').read_bytes()).hexdigest(),
                                   'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
                                   'reason':'GitHub runner uses official Debian mirror; original kept unchanged; base/project/build/output preserved.'},indent=2)+'\n')


if __name__=='__main__':main()
