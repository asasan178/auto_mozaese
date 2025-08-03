#!/usr/bin/env python3
"""
Developer spec file generator for Auto Mosaic
"""
import shutil
import os

def create_developer_spec():
    # Base spec should be in builds directory 
    base_spec = 'build_distribution_optimized.spec'
    dev_spec = 'build_developer.spec'
    
    # Check if we're in builds directory
    if os.path.basename(os.getcwd()) == 'builds':
        # We're in builds, use local files
        base_spec = 'build_distribution_optimized.spec'
        dev_spec = 'build_developer.spec'
    else:
        # We're in project root, look in builds
        base_spec = 'builds/build_distribution_optimized.spec'
        dev_spec = 'builds/build_developer.spec'

    if os.path.exists(base_spec):
        with open(base_spec, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Modify for developer version
        content = content.replace('build_lightweight', 'build_developer')
        content = content.replace('自動モザエセ_軽量版', '自動モザエセ_開発版')
        
        # Add developer version settings
        content = content.replace(
            'console=False,',
            '''console=True,   # Developer version has console display enabled
        icon=None,
        optimize=0,  # Optimization disabled (retain debug info)
        strip=False, # Retain debug information
        upx=False,   # UPX compression disabled (for debugging)'''
        )
        
        # Additional data files for developers
        if '# Additional files for developer version' not in content:
            content = content.replace(
                '# Force include entire NudeNet package',
                '''# Additional files for developer version
            ('.developer_mode', '.'),
            
            # Force include entire NudeNet package'''
            )
        
        with open(dev_spec, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print('    ✅ Developer spec file generated')
        return True
    else:
        print('    ❌ Base spec file not found')
        print(f'    [INFO] Looking for: {os.path.abspath(base_spec)}')
        print(f'    [INFO] Current directory: {os.getcwd()}')
        return False

if __name__ == "__main__":
    create_developer_spec() 