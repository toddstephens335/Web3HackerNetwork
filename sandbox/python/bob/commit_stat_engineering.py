import os
import json

def find_files(name, path):
    result = []
    for root, dirs, files in os.walk(path):
        if name in files:
            result.append(os.path.join(root, name))
    return result

def parse_commits(commit_files):
    all_logs = []
    all_commits = []
    for file in commit_files:
        in_stats = json.loads(open(file, 'r').read());
        all_logs.append(in_stats)
        for commit in in_stats:
            all_commits.append(commit)
    return all_commits

def percent(numerator, denominator):
    if (numerator == 0): return 0
    truncated = int(100 * 100 * numerator / denominator)
    return truncated / 100

def extract_stats(commit):
    js_types = ['js', 'jsx', 'ts', 'tsx']
    rust_types = ['rs', 'toml'] # toml is the cargo config extension
    markdown_types = ['md']
    json_types = ['json']
    chars_per_text_line = 30 # just a heuristic for approximating relative weight
    
    if 'files' in commit:
        num_files = commit['files']
    else:
        num_files = commit['file']
    typeDict = commit['fileTypes']
    typeArray = [{'fileType': key, 'stats': typeDict[key]} for key in typeDict.keys()]
    textTypeArray = [typeEntry for typeEntry in typeArray if typeEntry['stats']['textLineCount'] > 0]
    binTypeArray = [typeEntry for typeEntry in typeArray if typeEntry['stats']['binByteCount'] > 0]
    
    statDict = {}
    statDict['commit'] = commit['commit']
    
    statDict['totalFiles'] = int(num_files)
    statDict['binFiles'] = sum([typeEntry['stats']['occurrences'] for typeEntry in binTypeArray])
    statDict['textFiles'] = sum([typeEntry['stats']['occurrences'] for typeEntry in textTypeArray])
    
    statDict['binBytes'] = sum([typeEntry['stats']['binByteCount'] for typeEntry in binTypeArray])
    statDict['textLines'] = sum([typeEntry['stats']['textLineCount'] for typeEntry in textTypeArray])
    
    statDict['totalBytes'] = statDict['textLines'] * chars_per_text_line + statDict['binBytes']
    statDict['pctBinBytes'] = percent(statDict['binBytes'], statDict['totalBytes'])
    statDict['pctTextBytes'] = percent(statDict['textLines'] * chars_per_text_line, statDict['totalBytes'])
    
    jsTypeArray = [typeEntry for typeEntry in typeArray if typeEntry['fileType'] in js_types]
    statDict['jsFiles'] = sum([typeEntry['stats']['occurrences'] for typeEntry in jsTypeArray])
    statDict['jsLines'] = sum([typeEntry['stats']['textLineCount'] for typeEntry in jsTypeArray])
    statDict['pctJsFiles'] = percent(statDict['jsFiles'], statDict['totalFiles'])
    statDict['pctJsLines'] = percent(statDict['jsLines'], statDict['textLines'])
    statDict['pctJsBytes'] = percent(statDict['jsLines'] * chars_per_text_line, statDict['totalBytes'])
    
    rustTypeArray = [typeEntry for typeEntry in typeArray if typeEntry['fileType'] in rust_types]
    statDict['rustFiles'] = sum([typeEntry['stats']['occurrences'] for typeEntry in rustTypeArray])
    statDict['rustLines'] = sum([typeEntry['stats']['textLineCount'] for typeEntry in rustTypeArray])
    statDict['pctRustFiles'] = percent(statDict['rustFiles'], statDict['totalFiles'])
    statDict['pctRustLines'] = percent(statDict['rustLines'], statDict['textLines'])
    statDict['pctRustBytes'] = percent(statDict['rustLines'] * chars_per_text_line, statDict['totalBytes'])
    
    markdownTypeArray = [typeEntry for typeEntry in typeArray if typeEntry['fileType'] in markdown_types]
    statDict['markdownFiles'] = sum([typeEntry['stats']['occurrences'] for typeEntry in markdownTypeArray])
    statDict['markdownLines'] = sum([typeEntry['stats']['textLineCount'] for typeEntry in markdownTypeArray])
    statDict['pctMarkdownFiles'] = percent(statDict['markdownFiles'], statDict['totalFiles'])
    statDict['pctMarkdownLines'] = percent(statDict['markdownLines'], statDict['textLines'])
    statDict['pctMarkdownBytes'] = percent(statDict['markdownLines'] * chars_per_text_line, statDict['totalBytes'])
    
    jsonTypeArray = [typeEntry for typeEntry in typeArray if typeEntry['fileType'] in json_types]
    statDict['jsonFiles'] = sum([typeEntry['stats']['occurrences'] for typeEntry in jsonTypeArray])
    statDict['jsonLines'] = sum([typeEntry['stats']['textLineCount'] for typeEntry in jsonTypeArray])
    statDict['pctJsonFiles'] = percent(statDict['jsonFiles'], statDict['totalFiles'])
    statDict['pctJsonLines'] = percent(statDict['jsonLines'], statDict['textLines'])
    statDict['pctJsonBytes'] = percent(statDict['jsonLines'] * chars_per_text_line, statDict['totalBytes'])

    return statDict

def get_stats_for_all_commits(commit_logs):
    all_commits = parse_commits(commit_logs)
    all_stats = []
    
    for commit in all_commits:
        commit_id = commit['commit']
        commit_stats = extract_stats(commit)
        all_stats.append(commit_stats)
    
    return all_stats