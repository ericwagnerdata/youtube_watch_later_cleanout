"""Cluster uncategorized videos with Claude and write categories back."""
from wl_cleanup.categorize import categorize_all

if __name__ == "__main__":
    categorize_all()
