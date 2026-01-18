"""
V18.1 Hybrid Engine Rollback Script

If V18.1 Hybrid Engine causes system instability or performance issues,
please run this script to rollback to V18 version.
"""

import os
import shutil
from datetime import datetime

def rollback_v18_1_hybrid_engine():
    """Rollback V18.1 Hybrid Engine to V18"""
    print("=" * 80)
    print("V18.1 Hybrid Engine Rollback Script")
    print("=" * 80)
    print(f"Rollback time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Backup current files
    print("Backup current files...")
    backup_dir = f"backup_v18_1_hybrid_engine_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        'logic/sector_analysis.py',
        'ui/v18_navigator.py',
        'test_v18_1_hybrid_engine_performance.py',
        'tools/generate_static_map.py'
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            shutil.copy(file_path, os.path.join(backup_dir, file_path))
            print(f"  Backed up: {file_path}")
    
    print(f"\nBackup completed, backup directory: {backup_dir}")
    
    # Rollback instructions
    print("\n" + "=" * 80)
    print("Rollback Instructions")
    print("=" * 80)
    print("\nPlease use Git to rollback to V18 version:")
    print("\n1. Check Git history:")
    print("   git log --oneline -10")
    print("\n2. Rollback to V18 commit:")
    print("   git checkout <V18_COMMIT_ID> logic/sector_analysis.py ui/v18_navigator.py")
    print("\n3. Or use Git reset:")
    print("   git reset --hard <V18_COMMIT_ID>")
    print("\n4. Commit rollback:")
    print("   git add .")
    print("   git commit -m 'Rollback: V18.1 Hybrid Engine -> V18'")
    print("\n5. Push to GitHub:")
    print("   git push origin master --force")
    
    print("\n" + "=" * 80)
    print("Important Notes")
    print("=" * 80)
    print("\n1. Please ensure current changes are committed before rollback")
    print("2. System restart required after rollback")
    print("3. Be careful when using --force push")
    print("4. Recommended to create a new branch for backup before rollback")
    
    print("\n" + "=" * 80)
    print("Alternative: Disable V18.1 Hybrid Engine")
    print("=" * 80)
    print("\nIf you want to keep V18.1 but disable it temporarily:")
    print("\n1. Open main.py")
    print("2. Add the following line:")
    print("   ENABLE_V18_NAVIGATOR = False")
    print("3. Restart the system")
    print("\nThis will disable V18.1 features without rolling back the code.")
    
    print("\nRollback script execution completed!")
    print()


if __name__ == '__main__':
    rollback_v18_1_hybrid_engine()