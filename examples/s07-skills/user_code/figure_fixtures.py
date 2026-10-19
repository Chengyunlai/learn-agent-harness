"""浏览器临时虚拟文件上的真实函数；不读宿主目录，无模型/进程替身。"""
import inspect
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
from runtime import read_header,scan_skills,build_system,load_skill
FUNCTIONS=(scan_skills,build_system,load_skill)
CASES={'scan_skills':['normal','mismatch','header'], 'build_system':['normal','empty','repeat'],
       'load_skill':['found','unknown','oversize','encoding','empty']}


def fixture_context(name,scenario):
    if scenario not in CASES[name]:raise ValueError('unknown scenario')
    setup='''from pathlib import Path
import re
import tempfile
scenario=SCENARIO
_temp=tempfile.TemporaryDirectory(prefix="lesson7-")
root=Path(_temp.name)
header="---\\nname: output-check\\ndescription: 核对Python输出与预期，运行前取得许可。\\n---\\n"
for key,description,body in [("output-check","核对Python输出与预期，运行前取得许可。","先读预期，再获准运行；报告退出码与完整输出。"),("sql-style","编写SQL时使用。","当前问题不需要SQL正文。")]:
    folder=root/key
    folder.mkdir()
    (folder/"SKILL.md").write_text("---\\nname: "+key+"\\ndescription: "+description+"\\n---\\n"+body,encoding="utf-8")
base="围绕用户问题，按宿主权限使用工具。"
requested="output-check"
'''.replace('SCENARIO',repr(scenario))
    setup+='\n'+inspect.getsource(read_header)
    if name!='scan_skills':setup+='\n'+inspect.getsource(scan_skills)+'\nregistry=scan_skills(root)\n'
    setup+='''
if scenario=="mismatch":(root/"output-check"/"SKILL.md").write_text(header.replace("name: output-check","name: other"),encoding="utf-8")
if scenario=="header":(root/"output-check"/"SKILL.md").write_text("没有头部",encoding="utf-8")
if scenario=="unknown":requested="../other"
if scenario=="oversize":(root/"output-check"/"SKILL.md").write_text(header+"x"*8193,encoding="utf-8")
if scenario=="encoding":(root/"output-check"/"SKILL.md").write_bytes(b"\\xff")
if scenario=="empty" and "registry" in globals():registry={}
'''
    if name=='load_skill' and scenario=='empty':setup+='registry=scan_skills(root)\n(root/"output-check"/"SKILL.md").write_bytes(b"")\n'
    call={'scan_skills':'scan_skills(root)','build_system':'build_system(registry,base)','load_skill':'load_skill(requested,registry)'}[name]
    entry='try:\n    observed='+call+'\n    print("读取目录："+", ".join(observed) if isinstance(observed,dict) else observed)\nexcept (ValueError,OSError,UnicodeError) as error:\n    observed={"error":str(error)}\n    print(str(error))'
    if scenario=='repeat':entry+='\nassert observed==build_system(registry,base)\nprint("再次生成相同，没有叠加目录。")'
    watch={'scan_skills':['registry','name','meta','observed'],
           'build_system':['lines','name','description','catalog','observed','registry'],
           'load_skill':['name','entry','raw','text','observed','registry']}[name]
    return {'setup':setup,'entry':entry,'watch':watch,'scopes':[name]}
