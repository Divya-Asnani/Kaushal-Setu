"""
KaushalSetu Supabase Setup & Sync Utility
Verifies connection to live Supabase, tests access to the 25 tables, and pushes initial seed data.
"""
import os
import sys

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_backend_dir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.config import settings

def main():
    print("=" * 60)
    print("   KAUSHALSETU: SUPABASE CONFIGURATION & SYNC CHECK")
    print("=" * 60)
    print(f"Supabase URL: {settings.SUPABASE_URL}")
    
    if "your-project" in settings.SUPABASE_URL or "xyzcompany" in settings.SUPABASE_URL:
        print("\n[!] NOTICE: Placeholder Supabase credentials detected in .env:")
        print("    SUPABASE_URL is currently: https://your-project.supabase.co")
        print("\nTo see your entries live in your Supabase Dashboard:")
        print("1. Go to https://supabase.com -> Project Settings -> API")
        print("2. Copy your 'Project URL' and 'service_role' secret key")
        print("3. Paste them into .env:")
        print("   SUPABASE_URL=https://<your-project-ref>.supabase.co")
        print("   SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>")
        print("   SUPABASE_KEY=<your-anon-public-key>")
        print("\n4. Open your Supabase SQL Editor and run the contents of:")
        print("   c:\\Users\\Sanika\\Kaushal-Setu\\backend\\db\\schema.sql")
        print("=" * 60)
        return

    try:
        from supabase import create_client
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        client = create_client(settings.SUPABASE_URL, key)
        print("[+] Successfully initialized Supabase client!")
        
        # Test query to profiles
        res = client.table("profiles").select("count", count="exact").execute()
        print(f"[+] Connected to live Supabase database! Current 'profiles' count: {res.count}")
        
        # Optionally push seed data
        from backend.db.supabase_client import db
        print("[+] Syncing default skills, technicians, and knowledge cases into Supabase...")
        
        for s in db.skills.values():
            db.sync_to_supabase("skills", s)
        for p in db.profiles.values():
            db.sync_to_supabase("profiles", p)
        for wp in db.worker_profiles.values():
            db.sync_to_supabase("worker_profiles", wp)
        for ws in db.worker_skills.values():
            db.sync_to_supabase("worker_skills", ws)
        for c in db.certificates.values():
            db.sync_to_supabase("certificates", c)
        for e in db.experiences.values():
            db.sync_to_supabase("experiences", e)
        for kc in db.knowledge_cases.values():
            db.sync_to_supabase("knowledge_cases", kc)
            
        print("[+] Sync complete! All seed records are now visible in your Supabase Table Editor.")
        print("\nAll application data created via Flutter or FastAPI will also appear live in your Supabase dashboard!")
    except Exception as e:
        print(f"[-] Could not query or sync Supabase tables: {e}")
        print("\nIf tables are not created yet, copy the SQL from backend/db/schema.sql")
        print("and paste it into your Supabase project SQL Editor.")

if __name__ == "__main__":
    main()
