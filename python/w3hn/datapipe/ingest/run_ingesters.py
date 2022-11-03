# ========= External Libraries =================
import bz2
import datetime
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
# ----------------------------------------------

# ========== Project Root Path =================
this_path = os.path.abspath(sys.path[0])
project_dir = 'Web3HackerNetwork'
w3hndex = this_path.index(project_dir)
root_path = this_path[0:w3hndex + len(project_dir)]
# ---------- Local Library Path ----------------
# sys.path.insert(0, f'{root_path}/python')
# ---------- Local Libraries -------------------
from w3hn.datapipe.ingest.blame import BlameIngester
from w3hn.datapipe.ingest.dependency import DependencyIngester
from w3hn.datapipe.ingest.file_hacker_commit import FileHackerCommitIngester
from w3hn.datapipe.ingest.repo_file import RepoFileIngester
from w3hn.aws.aws_util import S3Util
import w3hn.hadoop.parquet_util as pq_util
# ----------------------------------------------

TEST_MODE = True
FULL_REFRESH = False
BLAME_JOB = 1
DEPS_JOB = 2
FILE_HACKER_JOB = 4
REPO_FILE_JOB = 8
JOBS = BLAME_JOB | DEPS_JOB | FILE_HACKER_JOB | REPO_FILE_JOB

old_file = 'ls-numstat-bucket-repo-5.log.bz2'
new_file = 'ls-numstat-bucket-repo-6.log.bz2'

low_partition_limit = '00' # '00' for all
high_partition_limit = 'ff' # 'ff' for all

# latest_file = 'dependency_map_files_new_2022-10-29.txt'
# latest_file = '2022-10-30-full-dependency-list.log'
# latest_file = 'foo.log'
file_data_path = f'{root_path}/data/files'
# deps_log = f'{file_data_path}/{latest_file}'
old_path = f'{file_data_path}/{old_file}'
new_path = f'{file_data_path}/{new_file}'

json_s3_util = S3Util(profile="enigmatt")

def parse_s3_list(lines):
    repos = dict()
    for line in lines():
        line_parts = re.split(' +', line)
        date = line_parts[0]
        time = line_parts[1]
        size = line_parts[2]
        path = line_parts[3]
        path_parts = re.split('/', path)
        owner = path_parts[1]
        repo_name = path_parts[2]
        file_type = path_parts[3]
        key = (owner, repo_name)
        if key not in repos: repos[key] = dict()
        repo = repos[key]
        entry = {'date': date,
                 'time': time,
                 'size': size,
                 'path': path}
        repo[file_type] = entry
    return repos

def diff_s3_list(old_lines, new_lines):
    old_lines = set(old_lines)
    diffed_lines = list()
    for line in new_lines:
        if line not in old_lines:
            diffed_lines.append(line)
    return diffed_lines

s3_file_metadata_dir = 'web3hackernetwork/metadata/files'
old_file = 'numstat_bucket_repo_files.5.log.bz2'
new_file = 'numstat_bucket_repo_files.6.log.bz2'
old_s3_ls_key = f'{s3_file_metadata_dir}/{old_file}'
new_s3_ls_key = f'{s3_file_metadata_dir}/{new_file}'

w3hn_s3_util = S3Util(profile='w3hn-admin', bucket_name='deadmandao')
old_lines = w3hn_s3_util.get_text_lines_from_bz2(old_s3_ls_key)
new_lines = w3hn_s3_util.get_text_lines_from_bz2(new_s3_ls_key)
lines = diff_s3_list(old_lines, new_lines)
for line in lines[1:10]:
    print(line)
print(f'num text lines: {len(lines)}')
# print(f'{lines[1:10]}')
exit()
old_lines = read_s3_list(old_path)
new_lines = read_s3_list(new_path, old_lines)
print(f'old len: {len(old_lines)}, new len: {len(new_lines)}')
exit()

def multi_phile():
    # repo_tuple_array = list()
    count = 0
    start = datetime.datetime.now()
    numstat_tuple_dict = dict()
    with open(deps_log, 'r') as f:
        lines = f.readlines()
        for line in lines:
            count += 1
            # if count > 100: break
            line = line.strip()
            path = line[slice(line.index('\t') + 1, len(line))]
            tail = path[slice(path.index('/') + 1, len(path))]
            owner = tail[slice(0,tail.index('/'))]
            tail = tail[slice(tail.index('/') + 1, len(tail))]
            repo_name = tail[slice(0,tail.index('/'))]
            partition_key = pq_util.repo_partition_key(owner, repo_name)
            if partition_key not in numstat_tuple_dict:
                numstat_tuple_dict[partition_key] = list()
            numstat_tuple_dict[partition_key].append((owner, repo_name))
    keys = list(numstat_tuple_dict.keys())
    keys.sort()
    for partition_key in keys:
        if partition_key < low_partition_limit:
            # print(f'skipping {partition_key}')
            continue
        elif partition_key > high_partition_limit:
            # print(f'skipping {partition_key}')
            continue
        else:
            print(f'{partition_key} is in bounds, running')
        print(datetime.datetime.now())
        numstat_tuple_list = numstat_tuple_dict[partition_key]
        repo_tuple_array = list()
        with ThreadPoolExecutor(max_workers=10) as executor:
            threadmap = executor.map(load_numstat, numstat_tuple_list)
        for result in threadmap:
            if result != None:
                repo_tuple_array.append(result)
        print(datetime.datetime.now())
        print('starting threadpool for parquet update jobs')
        if len(repo_tuple_array) > 0:
            futures = list()
            with ThreadPoolExecutor(max_workers=10) as executor:
                if JOBS & BLAME_JOB:
                    future = executor.submit(update_blame, repo_tuple_array)
                    futures.append(future)
                    print('blame job submitted')
                if JOBS & DEPS_JOB:
                    future = executor.submit(update_dependency, repo_tuple_array)
                    futures.append(future)
                    print('deps job submitted')
                if JOBS & FILE_HACKER_JOB:
                    future = executor.submit(update_file_hacker, repo_tuple_array)
                    futures.append(future)
                    print('file_hacker job submitted')
                if JOBS & REPO_FILE_JOB:
                    future = executor.submit(update_repo_file, repo_tuple_array)
                    futures.append(future)
                    print('repo_file job submitted')
            for future in futures:
                try:
                    future.result()
                except Exception as exc:
                    raise exc
                

def load_numstat(numstat_tuple):
    owner = numstat_tuple[0]
    repo_name = numstat_tuple[1]
    try:
        # print(f'reading numstat {count} of {len(numstat_tuple_list)}'
        #       f' for partition {partition_key} {owner} {repo_name}')
        blame_object = None
        deps_object = None
        numstat_object = None
        if JOBS & BLAME_JOB:
            print(f'reading blame for partition {owner} {repo_name}')
            blame_object = json_s3_util.get_blame_map(owner, repo_name)
        if JOBS & DEPS_JOB:
            print(f'reading deps for partition {owner} {repo_name}')
            deps_object = json_s3_util.get_dependency_map(owner, repo_name)
        if JOBS & (FILE_HACKER_JOB | REPO_FILE_JOB):
            print(f'reading numstat for partition {owner} {repo_name}')
            numstat_object = json_s3_util.get_numstat(owner, repo_name)
        repo_tuple = (owner, repo_name, blame_object, deps_object, numstat_object)
        return repo_tuple
    except Exception as error:
        print(f'error reading json {owner} {repo_name}: {error}')
    return None

def update_blame(repo_tuple_array):
    if TEST_MODE:
        print(f'not running BLAME on {len(repo_tuple_array)} repo_tuples')
    else:
        print(f'running BLAME on {len(repo_tuple_array)} repo_tuples')
        BlameIngester.update_repos(repo_tuple_array)

def update_dependency(repo_tuple_array):
    if TEST_MODE:
        print(f'not running DEPS on {len(repo_tuple_array)} repo_tuples')
    else:
        print(f'running DEPS on {len(repo_tuple_array)} repo_tuples')
        DependencyIngester.update_repos(repo_tuple_array)

def update_file_hacker(repo_tuple_array):
    if TEST_MODE:
        print(f'not running FILE_HACKER on {len(repo_tuple_array)} repo_tuples')
    else:
        print(f'running FILE_HACKER on {len(repo_tuple_array)} repo_tuples')
        FileHackerCommitIngester.update_repos(repo_tuple_array)

def update_repo_file(repo_tuple_array):
    if TEST_MODE:
        print(f'not running REPO_FILE on {len(repo_tuple_array)} repo_tuples')
    else:
        print(f'running REPO_FILE on {len(repo_tuple_array)} repo_tuples')
        RepoFileIngester.update_repos(repo_tuple_array)
            
multi_phile()