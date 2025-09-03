import os
from supabase import create_client, Client

# Use the SERVICE_ROLE key here for server-side access
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # <-- new

# Create client with service role key (bypasses RLS)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def get_recipients():
    """Fetching all active email addresses from Supabase, bypassing RLS."""
    data = supabase.table("recipients").select("email").eq("active", True).execute()
    if data.data:
        return [r["email"] for r in data.data]
    return []
