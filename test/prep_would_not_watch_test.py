#!/usr/bin/env python3
"""
Test Prep Script for would_not_watch Endpoint

Sets up test data for manual testing via center-console:
1. Resets training label to would_watch
2. Copies test media file to library path
3. Adds torrent to Transmission

After running this script, manually trigger would_not_watch via center-console
and verify:
- File is deleted from library
- Torrent is removed from Transmission
- Label is set to would_not_watch
"""
import os
import shutil
import psycopg2
from pathlib import Path
from transmission_rpc import Client as TransmissionClient
from transmission_rpc.error import TransmissionError

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "test" / "fixtures"
FIXTURE_MEDIA_DIR = FIXTURES_DIR / "media"

# Test data constants
TEST_IMDB_ID = "tt9999901"
TEST_HASH = "0000000000000000000000000000000099999901"
TEST_TORRENT_HASH = "55af51b9883b2e29e02fc728113747c706e480e3"
TEST_TORRENT_LINK = "https://yts.lt/torrent/download/55af51b9883b2e29e02fc728113747c706e480e3"
TARGET_DIR = "test-file-deletion-e2e-2002-1080p"


def load_env():
    """Load environment variables from .env file."""
    env_file = PROJECT_ROOT / ".env"
    env_vars = {}
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    value = value.strip("'\"")
                    env_vars[key] = value
                    os.environ[key] = value
    return env_vars


def reset_training_label(env_vars: dict) -> bool:
    """Reset training record to would_watch."""
    conn = psycopg2.connect(
        host=env_vars.get("REAR_DIFF_PGSQL_HOST"),
        port=env_vars.get("REAR_DIFF_PGSQL_PORT"),
        user=env_vars.get("REAR_DIFF_PGSQL_USERNAME"),
        password=env_vars.get("REAR_DIFF_PGSQL_PASSWORD"),
        dbname=env_vars.get("REAR_DIFF_PGSQL_DATABASE"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE atp.training
                SET label = 'would_watch',
                    human_labeled = false,
                    reviewed = false
                WHERE imdb_id = %s
                """,
                (TEST_IMDB_ID,),
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def update_media_parent_path(env_vars: dict, parent_path: str) -> bool:
    """Update the parent_path in atp.media."""
    conn = psycopg2.connect(
        host=env_vars.get("REAR_DIFF_PGSQL_HOST"),
        port=env_vars.get("REAR_DIFF_PGSQL_PORT"),
        user=env_vars.get("REAR_DIFF_PGSQL_USERNAME"),
        password=env_vars.get("REAR_DIFF_PGSQL_PASSWORD"),
        dbname=env_vars.get("REAR_DIFF_PGSQL_DATABASE"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE atp.media
                SET parent_path = %s
                WHERE hash = %s
                """,
                (parent_path, TEST_HASH),
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def copy_test_files(library_path: str) -> str:
    """Copy test files to library path."""
    dest_path = os.path.join(library_path, TARGET_DIR)

    # Remove if exists
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)

    # Create directory
    os.makedirs(dest_path, exist_ok=True)

    # Copy files
    for file in os.listdir(FIXTURE_MEDIA_DIR):
        src = os.path.join(FIXTURE_MEDIA_DIR, file)
        dst = os.path.join(dest_path, file)
        shutil.copy2(src, dst)

    # Set permissions
    os.chmod(dest_path, 0o775)
    for file in os.listdir(dest_path):
        os.chmod(os.path.join(dest_path, file), 0o775)

    return dest_path


def add_torrent(env_vars: dict) -> bool:
    """Add torrent to Transmission."""
    try:
        client = TransmissionClient(
            host=env_vars.get("REAR_DIFF_TRANSMISSION_HOST"),
            port=int(env_vars.get("REAR_DIFF_TRANSMISSION_PORT", "9091")),
            username=env_vars.get("REAR_DIFF_TRANSMISSION_USERNAME", ""),
            password=env_vars.get("REAR_DIFF_TRANSMISSION_PASSWORD", ""),
        )
        client.add_torrent(TEST_TORRENT_LINK)
        return True
    except TransmissionError as e:
        if "duplicate" in str(e).lower():
            return True
        print(f"Error adding torrent: {e}")
        return False


def torrent_exists(env_vars: dict) -> bool:
    """Check if torrent exists in Transmission."""
    try:
        client = TransmissionClient(
            host=env_vars.get("REAR_DIFF_TRANSMISSION_HOST"),
            port=int(env_vars.get("REAR_DIFF_TRANSMISSION_PORT", "9091")),
            username=env_vars.get("REAR_DIFF_TRANSMISSION_USERNAME", ""),
            password=env_vars.get("REAR_DIFF_TRANSMISSION_PASSWORD", ""),
        )
        client.get_torrent(TEST_TORRENT_HASH)
        return True
    except:
        return False


def main():
    print("=" * 60)
    print("would_not_watch Test Prep Script")
    print("=" * 60)

    # Load environment
    print("\n[1/5] Loading environment...")
    env_vars = load_env()
    library_path = env_vars.get("REAR_DIFF_MEDIA_LIBRARY_PATH_MOVIES", "").rstrip("/")
    print(f"      Library path: {library_path}")

    # Reset training label
    print("\n[2/5] Resetting training label to 'would_watch'...")
    if reset_training_label(env_vars):
        print(f"      OK - {TEST_IMDB_ID} reset to would_watch")
    else:
        print(f"      WARN - No record found for {TEST_IMDB_ID}")

    # Copy test files
    print("\n[3/5] Copying test files to library...")
    dest_path = copy_test_files(library_path)
    files = os.listdir(dest_path)
    print(f"      OK - Copied {len(files)} file(s) to {dest_path}")
    for f in files:
        print(f"          - {f}")

    # Update media parent_path
    print("\n[4/5] Updating media parent_path in database...")
    if update_media_parent_path(env_vars, library_path):
        print(f"      OK - parent_path set to {library_path}")
    else:
        print(f"      WARN - No media record found for hash {TEST_HASH}")

    # Add torrent
    print("\n[5/5] Adding torrent to Transmission...")
    if add_torrent(env_vars):
        print(f"      OK - Torrent added: {TEST_TORRENT_HASH[:16]}...")
    else:
        print("      FAIL - Could not add torrent")

    # Verify setup
    print("\n" + "=" * 60)
    print("SETUP COMPLETE - Ready for manual test")
    print("=" * 60)
    print(f"""
Test Record:
  IMDB ID:      {TEST_IMDB_ID}
  Media Title:  Test Movie - File Deletion E2E
  Label:        would_watch (ready to be changed)

Files:
  Path:         {dest_path}
  Exists:       {os.path.exists(dest_path)}

Torrent:
  Hash:         {TEST_TORRENT_HASH}
  In Transmission: {torrent_exists(env_vars)}

Next Steps:
  1. Open center-console
  2. Find record {TEST_IMDB_ID}
  3. Click 'would_not_watch' button
  4. Verify:
     - File deleted: {dest_path}
     - Torrent removed from Transmission
     - Label changed to 'would_not_watch'
""")


if __name__ == "__main__":
    main()
