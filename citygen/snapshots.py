import math
from datetime import datetime

def compute_snapshots(commits, config):
    """
    Compute snapshots using the numstat method (approximate).
    """
    if len(commits) < 10:
        return None
        
    num_snapshots = config.get("snapshots", 24)
    if num_snapshots < 2:
        return None
        
    # Sort commits by timestamp ascending
    sorted_commits = sorted(commits, key=lambda c: c['timestamp'])
    first_ts = sorted_commits[0]['timestamp']
    last_ts = sorted_commits[-1]['timestamp']
    
    # Calculate target timestamps
    dt = (last_ts - first_ts) / (num_snapshots - 1)
    target_times = [first_ts + dt * i for i in range(num_snapshots)]
    
    # Track state
    file_loc = {}
    file_born = {}
    file_died = {}
    file_max_loc = {}
    
    snapshots_data = {
        "method": "numstat",
        "ts": target_times,
        "labels": [datetime.utcfromtimestamp(t).strftime('%Y-%m-%d') for t in target_times],
        "commits": [],
        "stats": [],
        "delta": [{} for _ in range(num_snapshots)]
    }
    
    commit_idx = 0
    total_commits = len(sorted_commits)
    
    authors_active_set = set()
    commits_since_last = 0
    
    for snap_idx, target_time in enumerate(target_times):
        # Consume commits up to target_time
        while commit_idx < total_commits and sorted_commits[commit_idx]['timestamp'] <= target_time:
            c = sorted_commits[commit_idx]
            authors_active_set.add(c['author'])
            commits_since_last += 1
            
            for path, stats in c.get('files', {}).items():
                if path not in file_loc:
                    file_loc[path] = 0
                    file_born[path] = c['timestamp']
                    if path in file_died:
                        del file_died[path]
                
                # Assume numstat is dict with adds, dels
                adds = stats.get('adds', 0)
                dels = stats.get('dels', 0)
                file_loc[path] = max(0, file_loc[path] + adds - dels)
                
                # Check for deletions
                if file_loc[path] == 0 and dels > 0 and adds == 0:
                    file_died[path] = c['timestamp']
                    file_loc[path] = 0
                    
                file_max_loc[path] = max(file_max_loc.get(path, 0), file_loc[path])
                
            commit_idx += 1
            
        # Snapshot state
        snap_sha = sorted_commits[commit_idx - 1]['hash'] if commit_idx > 0 else sorted_commits[0]['hash']
        snapshots_data["commits"].append(snap_sha)
        
        # We don't populate delta here, we'll do it later when we have building indices
        
        # Stats
        total_loc = sum(loc for p, loc in file_loc.items() if p not in file_died)
        active_files = sum(1 for p in file_loc if p not in file_died)
        
        snapshots_data["stats"].append({
            "files": active_files,
            "loc": total_loc,
            "authors_active": len(authors_active_set),
            "commits_since": commits_since_last
        })
        
        authors_active_set.clear()
        commits_since_last = 0
        
    return {
        "snapshots": snapshots_data,
        "file_loc": file_loc,
        "file_born": file_born,
        "file_died": file_died,
        "file_max_loc": file_max_loc
    }

def populate_deltas(snapshots_data, file_loc_history, buildings):
    # This requires running the walk again or storing full state history.
    # To save memory, we can store state per snapshot in the previous loop.
    pass
