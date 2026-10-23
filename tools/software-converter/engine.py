"""Local conversion engine. No network calls, models, or automatic installs."""
from __future__ import annotations
import ast
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import struct
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path

SKIP = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', 'dist', 'build', '.idea'}
MAX_BYTES = 256 * 1024 * 1024
MAX_FILES = 10000
METHODS = ['Smart Auto', 'Direct', 'Hybrid', 'Behavioral rebuild', 'Compatibility', 'AI Assist']

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def inventory(root):
    root = Path(root).resolve()
    result, total = [], 0
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not (Path(base)/d).is_symlink())
        for name in sorted(files):
            p = Path(base)/name
            if p.is_symlink():
                raise ValueError('Source symlinks are not supported: ' + str(p))
            total += p.stat().st_size
            if total > MAX_BYTES or len(result) >= MAX_FILES:
                raise ValueError('Source exceeds the 256 MiB / 10,000 file inspection limit.')
            result.append({'path': p.relative_to(root).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)})
    return result

def unpack(source, target):
    """Validate all entries before extracting; no traversal, symlinks, or zip bombs."""
    target = Path(target).resolve()
    with zipfile.ZipFile(source) as z:
        entries = z.infolist()
        if len(entries) > MAX_FILES or sum(i.file_size for i in entries) > MAX_BYTES:
            raise ValueError('Archive exceeds inspection limits.')
        seen = set()
        for i in entries:
            name = i.filename.replace('\\', '/')
            parts = name.split('/')
            if name.startswith('/') or any(':' in x or x == '..' or x.rstrip(' .') != x for x in parts if x):
                raise ValueError('Unsafe archive path: ' + i.filename)
            p = (target/name).resolve()
            key = str(p).casefold()
            if not p.is_relative_to(target) or key in seen or ((i.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError('Unsafe or duplicate archive member: ' + i.filename)
            seen.add(key)
        z.extractall(target)

def inspect_source(source):
    source = Path(source).resolve()
    if not source.exists():
        raise ValueError('Input does not exist.')
    result = {'name': source.name, 'input': str(source), 'host': platform.system(), 'host_arch': platform.machine(),
              'format': 'unknown', 'source_os': 'unknown', 'architecture': 'unknown', 'entrypoints': [], 'imports': [],
              'excluded_directories': sorted(SKIP)}
    if source.is_dir():
        files = inventory(source)
        result['files'] = files
        py = [x['path'] for x in files if x['path'].endswith('.py')]
        preferred = [x for x in py if Path(x).name in ('main.py', '__main__.py', 'app.py', 'ai_notepad.py')]
        result.update(format='Python source' if py else 'Source directory', source_os='portable / undetermined',
                      entrypoints=preferred or py, root=str(source), sha256=hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest())
        imports = set()
        for name in py:
            try:
                tree = ast.parse((source/name).read_text(encoding='utf-8-sig'))
                for n in ast.walk(tree):
                    if isinstance(n, ast.Import): imports.update(x.name.split('.')[0] for x in n.names)
                    elif isinstance(n, ast.ImportFrom) and n.module: imports.add(n.module.split('.')[0])
            except (UnicodeError, SyntaxError):
                pass
        result['imports'] = sorted(imports)
        return result
    if source.stat().st_size > MAX_BYTES:
        raise ValueError('Input exceeds 256 MiB.')
    result['sha256'] = digest(source)
    with source.open('rb') as f: head = f.read(4096)
    if source.suffix.lower() == '.py':
        result.update(format='Python source', root=str(source.parent), entrypoints=[source.name], source_os='portable / undetermined', single_file=True)
    elif head[:2] == b'MZ':
        arch = 'unknown'
        if len(head) >= 64:
            off = struct.unpack_from('<I', head, 60)[0]
            with source.open('rb') as f:
                f.seek(off); pe = f.read(6)
            if pe[:4] == b'PE\0\0':
                arch = {0x8664:'x64',0x14c:'x86',0xaa64:'ARM64'}.get(struct.unpack_from('<H', pe, 4)[0], 'unknown')
        result.update(format='PE executable', source_os='Windows', architecture=arch)
    elif head[:4] == b'\x7fELF':
        result.update(format='ELF executable', source_os='Linux / Unix', architecture={1:'32-bit',2:'64-bit'}.get(head[4], 'unknown'))
    elif head[:4] in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe'):
        result.update(format='Mach-O', source_os='macOS')
    elif zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as z:
            names = z.namelist()
        kind = 'APK' if 'AndroidManifest.xml' in names else 'AAB' if 'BundleConfig.pb' in names else 'ZIP archive'
        result.update(format=kind, source_os='Android' if kind in ('APK','AAB') else 'undetermined', members=len(names))
    else:
        result['format'] = {'.msi':'MSI package', '.dmg':'DMG package', '.appimage':'AppImage'}.get(source.suffix.lower(), 'Unknown binary / file')
    return result

class Store:
    def __init__(self, root):
        self.root = Path(root).resolve(); self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root/'jobs.sqlite'
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, created REAL, status TEXT, data TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS recipes (key TEXT PRIMARY KEY, successes INTEGER, failures INTEGER, data TEXT)')
    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.db, timeout=30)
        try:
            with connection:
                yield connection
        finally:
            connection.close()
    def save(self, data):
        with self.connect() as c:
            c.execute('INSERT OR REPLACE INTO jobs VALUES (?,?,?,?)', (data['id'], data['created'], data['status'], json.dumps(data)))
        p = self.root/'jobs'/data['id']; p.mkdir(parents=True, exist_ok=True)
        (p/'receipt.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    def jobs(self):
        with self.connect() as c: return [json.loads(x[0]) for x in c.execute('SELECT data FROM jobs ORDER BY created DESC')]
    def recipes(self):
        with self.connect() as c: return [dict(key=k,successes=s,failures=f,**json.loads(d)) for k,s,f,d in c.execute('SELECT * FROM recipes')]
    def record_recipe(self, key, success, data):
        with self.connect() as c:
            c.execute('INSERT INTO recipes VALUES (?,?,?,?) ON CONFLICT(key) DO UPDATE SET successes=successes+excluded.successes, failures=failures+excluded.failures, data=excluded.data',
                      (key, int(success), int(not success), json.dumps(data)))

class Cancelled(Exception): pass

class Engine:
    def __init__(self, store, log=lambda s:None):
        self.store, self.log = store, log
        self.stop = threading.Event()
    def run_command(self, args, cwd, logfile, timeout=300):
        self.log('Running: ' + subprocess.list2cmdline([str(x) for x in args]))
        start = time.monotonic()
        with Path(logfile).open('w', encoding='utf-8') as out:
            frozen_windows = os.name == 'nt' and getattr(sys, 'frozen', False)
            if frozen_windows:
                import ctypes
                ctypes.windll.kernel32.SetDllDirectoryW(None)
            try:
                p = subprocess.Popen([str(x) for x in args], cwd=cwd, stdout=out, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, start_new_session=os.name != 'nt')
            finally:
                if frozen_windows: ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))
            try:
                while p.poll() is None:
                    if self.stop.wait(.15): raise Cancelled('Stopped by user')
                    if time.monotonic()-start > timeout: raise TimeoutError('Command exceeded time limit')
            finally:
                if p.poll() is None:
                    if os.name == 'nt': subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        import signal
                        os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
        text = Path(logfile).read_text(encoding='utf-8', errors='replace')
        return {'exit_code': p.returncode, 'output': text[-200000:], 'seconds': round(time.monotonic()-start, 2), 'log':str(logfile)}

    def convert(self, source, targets, method='Smart Auto', python='', entry='', test_args=None, allow_execution=False):
        data = {'id':uuid.uuid4().hex[:12], 'created':time.time(), 'status':'INSPECTING', 'source':str(source),
                'method_requested':method, 'targets':[], 'ai_called':False, 'external_uploads':False, 'execution_allowed':allow_execution}
        job = self.store.root/'jobs'/data['id']; job.mkdir(parents=True)
        self.store.save(data)
        try:
            source = Path(source).resolve()
            if source.is_dir() and self.store.root.is_relative_to(source):
                raise ValueError('Job storage must be outside the input directory.')
            info = inspect_source(source); data['inspection'] = info
            if info['format'] == 'ZIP archive':
                unpack(source, job/'source'); info = inspect_source(job/'source'); data['expanded_inspection'] = info
            elif info['format'] == 'Python source':
                stage = job/'source'; stage.mkdir()
                if info.get('single_file'): shutil.copy2(source, stage/source.name)
                else:
                    for record in info['files']:
                        p = stage/record['path']; p.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source/record['path'], p)
                info = inspect_source(stage)
            entries = info.get('entrypoints', [])
            entry = entry or (entries[0] if len(entries)==1 else '')
            root = Path(info.get('root', job))
            if entry and (not (root/entry).resolve().is_relative_to(root.resolve()) or not (root/entry).is_file()):
                raise ValueError('Entrypoint must be an existing file inside the staged project.')
            for target in targets:
                if self.stop.is_set(): raise Cancelled('Stopped by user')
                osname, fmt = target
                result = {'os':osname,'format':fmt,'status':'UNRESOLVED','coverage':[], 'limitations':[]}
                data['targets'].append(result)
                self.log(f'{osname} / {fmt}: selecting a local method')
                native = {'Windows':'EXE','Linux':'Executable'}.get(platform.system())
                if osname != platform.system() or fmt != native:
                    result['reason'] = 'No installed adapter for this destination. A matching build environment and packaging adapter are required.'
                elif method not in ('Smart Auto','Direct','AI Assist'):
                    result['reason'] = f'{method} adapter is not implemented in this release; diagnostic handoff required.'
                elif info['format'] != 'Python source' or not entry:
                    result['reason'] = 'This adapter requires Python source and one selected entrypoint. Binary-only reconstruction is unresolved.'
                elif not python or not Path(python).is_file():
                    result['reason'] = 'Configure a Python interpreter with PyInstaller and the project dependencies.'
                else:
                    probe = self.run_command([python,'-c','import sys,platform,PyInstaller,importlib.metadata,json; print(sys.version); print(platform.machine()); print(PyInstaller.__version__); print(json.dumps(sorted((d.metadata.get("Name",""),d.version) for d in importlib.metadata.distributions())))'], root, job/f'{osname}-toolchain.log', 30)
                    if probe['exit_code']:
                        result['reason']='Configured interpreter cannot import PyInstaller.'; self.store.save(data); continue
                    key=hashlib.sha256(json.dumps([info['sha256'],entry,osname,fmt,probe['output'],test_args],sort_keys=True).encode()).hexdigest()
                    prior=next((r for r in self.store.recipes() if r['key']==key and r['successes']),None)
                    result.update(method='Direct / PyInstaller',recipe_reused=bool(prior),toolchain=probe['output'])
                    baseline=None
                    if allow_execution and test_args is not None:
                        data['status']='BASELINE'; self.store.save(data)
                        baseline=self.run_command([python,root/entry,*test_args],root,job/f'{osname}-baseline.log',30)
                        result['baseline']=baseline
                        if baseline['exit_code']:
                            result['reason']='Source baseline failed; fix it before conversion.'; self.store.save(data); continue
                    data['status']='BUILDING'; self.store.save(data)
                    out=job/'output'/osname; work=job/'build'/osname
                    build=self.run_command([python,'-m','PyInstaller','--noconfirm','--clean','--onefile','--name','ConvertedApp','--distpath',out,'--workpath',work,'--specpath',work,root/entry],root,job/f'{osname}-build.log',600)
                    result['build'] = build
                    artifact=out/('ConvertedApp.exe' if osname=='Windows' else 'ConvertedApp')
                    if build['exit_code'] or not artifact.is_file():
                        result['reason']='Build failed; see build log.'; self.store.record_recipe(key,False,{'method':'PyInstaller','target':osname,'source_hash':info['sha256']})
                    else:
                        result.update(status='BUILT_UNTESTED',artifact=str(artifact),sha256=digest(artifact),bytes=artifact.stat().st_size)
                        result['coverage']=['Output file exists','Output SHA-256 recorded']
                        result['limitations']=['No exhaustive GUI or functional equivalence claim.','Build uses configured dependencies; no automatic dependency installation.']
                        if baseline:
                            data['status']='VERIFYING'; self.store.save(data)
                            tested=self.run_command([artifact,*test_args],out,job/f'{osname}-output-test.log',30)
                            result['test']=tested
                            passed=tested['exit_code']==baseline['exit_code']==0 and tested['output'].strip()==baseline['output'].strip()
                            result['status']='VERIFIED_SELECTED_TEST' if passed else 'PARTIAL'
                            result['coverage'].append('Compared source and packaged exit codes and stdout for the explicitly selected test')
                            if not passed: result['reason']='Packaged behavior differs from source baseline.'
                            self.store.record_recipe(key,passed,{'method':'PyInstaller','target':osname,'source_hash':info['sha256'],'test_args':test_args,'coverage':'selected test only'})
                self.store.save(data)
            states=[r['status'] for r in data['targets']]
            data['status']='VERIFIED_SELECTED_TEST' if states and all(s=='VERIFIED_SELECTED_TEST' for s in states) else 'BUILT_UNTESTED' if states and all(s=='BUILT_UNTESTED' for s in states) else 'PARTIAL' if any(s in ('BUILT_UNTESTED','VERIFIED_SELECTED_TEST','PARTIAL') for s in states) else 'UNRESOLVED'
        except Cancelled as e: data.update(status='CANCELLED',error=str(e))
        except Exception as e: data.update(status='FAILED',error=str(e)); self.log(str(e))
        self.store.save(data)
        if data['status'] in ('UNRESOLVED','PARTIAL','FAILED'):
            handoff=job/'AI-HANDOFF.zip'
            instructions='Continue this conversion from receipt.json and logs. Preserve working targets. Identify missing source, tools, adapters, and verification coverage. Return patches and tests. Do not claim an untested output works. Source code is not included; ask the owner to share only what is needed.'
            with zipfile.ZipFile(handoff,'w',zipfile.ZIP_DEFLATED) as z:
                z.writestr('HANDOFF.md',instructions)
                z.write(job/'receipt.json','receipt.json')
                for log in job.glob('*.log'): z.write(log,log.name)
            data['handoff']=str(handoff); self.store.save(data)
        self.log('Finished: '+data['status'])
        return data
