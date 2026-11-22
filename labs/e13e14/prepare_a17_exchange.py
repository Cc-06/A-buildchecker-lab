"""Create A17's maintained C/Make project and a portable history bundle."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'labs/e8e10')]
from lab import fixture, commit, run, scan


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    dest=ROOT/'data/e13-a17-241880606'
    if dest.exists():
        raise ValueError('Preserve existing project; use its recorded manifest')
    repo=dest/'repo'
    fixture(repo,style='mixed')
    origin=run(['git','rev-parse','HEAD'],repo).strip()
    run(['git','config','user.name','241880606'],repo)
    run(['git','config','user.email','241880606@smail.nju.edu.cn'],repo)
    # Student addition: a cancelling calculation and regression assertions.
    (repo/'helper.c').write_text('static int twice(int x){return x*2;}\nint helper(void){return twice(17)-34;}\n')
    (repo/'regression.py').write_text('import subprocess\nsubprocess.run(["make","clean"],check=True)\nsubprocess.run(["make","app"],check=True)\nassert subprocess.check_output(["./app"],text=True).strip()=="1"\n')
    broken='FROM python:3.13-slim\nWORKDIR /work\nCOPY main.c helper.c config.h extra.h unused.h Makefile ./\nRUN make app\nCMD ["./app"]\n'
    (repo/'Dockerfile.broken').write_text(broken)
    base=commit(repo,'A17 add tested cancelling calculation and build container input')
    (repo/'main.c').write_text('#include "extra.h"\n'+(repo/'main.c').read_text().replace('VALUE+helper()','VALUE+helper()+EXTRA'))
    (repo/'README.md').write_text('A17 陈佶哲 241880606\n来源：labs/e8e10/lab.py fixture(mixed)。新增 helper 抵消计算、extra.h 实际参与表达式及 regression.py。\n正常输出1，config.h VALUE改为2后修复前缺失依赖会导致陈旧输出；修复后应为2。\n')
    target=commit(repo,'A17 use EXTRA in expression and retain missing dependency fault')
    run(['python3','regression.py'],repo)
    candidate=broken.replace('FROM python:3.13-slim','FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f').replace('RUN make app','RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*\nRUN make app')
    (dest/'candidate.Dockerfile').write_text(candidate)
    request={'mode':'e11-a','repo':'/course/data/e13-a17-241880606/repo','base':base,'target':target,'candidate':'/course/data/e13-a17-241880606/candidate.Dockerfile','expected_output':'1','header_change_output':'2','build_timeout':600}
    save(dest/'request-e11-a.json',request)
    save(dest/'request-e14.json',dict(request,mode='e12'))
    manifest={'provider':'A17','student_id':'241880606','name':'陈佶哲','consumer':'B17',
              'system_repository':'https://github.com/Cc-06/A-buildchecker-lab',
              'source':'Course labs/e8e10/lab.py fixture(mixed)', 'source_fixture_commit':origin,
              'adaptation':['tested helper cancelling calculation','extra.h used in main expression','student regression script and provenance'],
              'base':base,'target':target,'expected_output':'1','header_change_output':'2',
              'fault':'main.o omits config.h and extra.h dependencies',
              'limits':'two C sources, explicit Make rules; Linux gcc/make; build timeout600s; run only isolated snapshots'}
    save(dest/'manifest.json',manifest)
    run(['git','bundle','create',str(dest/'project.bundle'),'--all'],repo)
    export=ROOT/'exchange/a17'; export.mkdir(parents=True,exist_ok=True)
    for name in ('project.bundle','manifest.json','candidate.Dockerfile','request-e11-a.json','request-e14.json'):
        shutil.copyfile(dest/name,export/name)
    (export/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(export.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
