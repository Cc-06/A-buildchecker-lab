"""Keep received candidates immutable; record a local network adaptation."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def main():
    records=[]
    install="RUN sed -i 's|http://deb.debian.org|http://mirrors.cloud.aliyuncs.com|g' /etc/apt/sources.list.d/debian.sources && apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*"
    for relative in ('integration-sample','e13-a17-241880606','e13-b17-251880498'):
        root=ROOT/'data'/relative
        old=root/'candidate.Dockerfile'
        lines=old.read_text().splitlines()
        added=[line for line in lines if line.startswith('RUN ') and line!='RUN make app']
        new=[lines[0],install,*[line for line in lines[1:] if line not in added]]
        dest=root/'candidate-A17-local.Dockerfile'
        if dest.exists():raise ValueError('Preserve earlier candidate')
        dest.write_text('\n'.join(new)+'\n')
        request_path=root/('e12.json' if relative=='integration-sample' else 'request-e14.json')
        request=json.loads(request_path.read_text())
        request['candidate']='/course/data/'+relative+'/'+dest.name
        (root/'request-e14-local.json').write_text(json.dumps(request,indent=2)+'\n')
        records.append({'project':relative,'original_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
                        'local_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
                        'adaptation':'Retain base digest, project COPY/build/runtime; use cloud mirror and install before COPY for shared cache.',
                        'original_preserved':True})
    out=ROOT/'work/e14-evidence/local-candidates.json'
    out.write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
