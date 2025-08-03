#!/usr/bin/env python3
"""
Distribution spec file generator for Auto Mosaic
"""
import shutil
import os

def create_distribution_spec():
    # Base spec should be in project root relative to builds directory
    base_spec = '../build_distribution_optimized.spec'
    dist_spec = '../build_distribution.spec'
    
    # Check if we're in builds directory
    if os.path.basename(os.getcwd()) == 'builds':
        # We're in builds, use relative path to parent
        base_spec = '../build_distribution_optimized.spec'
        dist_spec = '../build_distribution.spec'
    else:
        # We're in project root
        base_spec = 'build_distribution_optimized.spec'
        dist_spec = 'build_distribution.spec'
    
    if os.path.exists(base_spec):
        with open(base_spec, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace build name references
        content = content.replace('build_lightweight', 'build_distribution')
        content = content.replace('自動モザエセ_軽量版', '自動モザエセ_配布版')
        
        with open(dist_spec, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print('    [OK] Distribution spec created')
        return True
    else:
        print('    [ERROR] Base spec file not found')
        print(f'    [INFO] Looking for: {os.path.abspath(base_spec)}')
        print(f'    [INFO] Current directory: {os.getcwd()}')
        return False

if __name__ == "__main__":
    create_distribution_spec() 