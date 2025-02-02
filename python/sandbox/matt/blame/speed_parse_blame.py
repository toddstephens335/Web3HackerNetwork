from time import perf_counter
# from lib.monitor import MultiprocessMonitor, timeit
from lib.signal_handler import SignalHandler
import os
import sys
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

def get_blame(repo_dir, file_path):
    cmd = ['git', '-C', repo_dir, 'blame', '--porcelain', file_path]
    handler = SignalHandler()
    success, stdout, stderr = handler.execute_os_cmd(cmd)
    stdout = str(stdout)
    stdout = re.sub('^b"', '', stdout)
    stdout = re.sub("^b'", '', stdout)
    stdout = re.sub('"$', '', stdout)
    stdout = stdout.replace('\\n', '\n')
    stdout = stdout.replace('\\t', '\t')
    # print(stdout)
    return stdout

class BlameGameRetriever(): #SignalHandler):
    def __init__(self):
        self.repo_dir = \
            './repos/pavanpoojary7/Sports-Tournaments'

        paths_file = \
            './repos/pavanpoojary7/js_files.txt'
        if not os.path.exists(paths_file):
            print('Loading '+paths_file+' before starting')
            self.load_file_list(self.repo_dir, paths_file)
        with open(paths_file, 'rt') as paths_in:
            self.paths = [line.strip() for line in paths_in.readlines()]
        print(f'File Count: {len(self.paths)}')
        # SignalHandler.__init__(self)


    def load_file_list(self, repo_dir, results):
        with open(results, 'wt') as f:
            for subdir, dirs, files in os.walk(repo_dir):
                for file in files:
                    if file.endswith('.js'):
                        f.write(os.path.join(subdir, file)+'\n')

    def do_it(self, path):
        #print(f'reading {path}')
        commit_lines_regex = '^([0-9a-f]{40}) [0-9]+ [0-9]+ ([0-9]+)$'
        gather_name_regex = '^author (.*)$'
        gather_mail_regex = '^author-mail (.*)$'
        relative_path = path.replace(self.repo_dir, '.')
        text = get_blame(self.repo_dir, relative_path)
        lines = text.splitlines(False)
        seek_commit_mode = True
        gather_mode = False
        commits = dict()
        for line in lines:
            if seek_commit_mode:
                commit_lines_matches = re.findall(commit_lines_regex, line)
                if commit_lines_matches:
                    # print(f'{matches}')
                    commit_id = commit_lines_matches[0][0]
                    line_count = int(commit_lines_matches[0][1])
                    if commit_id in commits:
                        commit = commits[commit_id]
                        # print(f'{commit_id} {line_count} {committer}')
                        commit['line_count'] += line_count
                    else:
                        seek_commit_mode = False
                        gather_mode = True
                        name = None
                        mail = None
            elif gather_mode:
                if not name:
                    name_matches = re.findall(gather_name_regex, line)
                    if name_matches:
                        name = name_matches[0]
                elif not mail:
                    mail_matches = re.findall(gather_mail_regex, line)
                    if mail_matches:
                        mail = mail_matches[0]
                if name and mail:
                    commits[commit_id] = {
                        'name':name,
                        'email':mail,
                        'line_count':line_count
                    }
                    # print(f'{commit_id} {line_count} {name} {mail}')
                    seek_commit_mode = True
                    gather_mode = False
        committers = dict()
        for commit_id, commit in commits.items():
            name = commit['name']
            email = commit['email']
            author = f'{name} <{email}>'
            if author not in committers:
                committers[author] = {'line_count':0, 'commit_count':0}
            committers[author]['line_count'] += commit['line_count']
            committers[author]['commit_count'] += 1
        return (path, committers)

    def do_it_with_files(self, max_workers=1):
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            threadmap = executor.map(self.do_it, self.paths[0:1000])
        # for result in threadmap:
        #     print(f'{result}')
        
if __name__ == '__main__':
    bgr = BlameGameRetriever()
    for n_threads in range(1,21):
        start = perf_counter()
        bgr.do_it_with_files(n_threads)
        end = perf_counter()
        print(f'Elapsed: {end-start} with {n_threads} threads')
